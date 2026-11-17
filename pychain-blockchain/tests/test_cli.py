"""End-to-end CLI test running in an isolated PYCHAIN_HOME."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pychain import cli, config, logger


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"PYCHAIN_HOME": self._tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        # Fast difficulty and a fresh logger config for the test run.
        diff = mock.patch.object(config, "DIFFICULTY", 2)
        diff.start()
        self.addCleanup(diff.stop)
        logger._configured = False
        for h in list(logger.logging.getLogger("pychain").handlers):
            logger.logging.getLogger("pychain").removeHandler(h)
            h.close()
        self.addCleanup(lambda: setattr(logger, "_configured", False))

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_full_workflow_and_files_are_written(self):
        self.assertEqual(self.run_cli("wallet", "create", "alice")[0], 0)
        self.assertEqual(self.run_cli("wallet", "create", "bob")[0], 0)
        self.assertEqual(self.run_cli("mine", "alice")[0], 0)
        self.assertEqual(self.run_cli("send", "alice", "bob", "12")[0], 0)
        self.assertEqual(self.run_cli("mine", "alice")[0], 0)
        _, out = self.run_cli("balance", "bob")
        self.assertIn("12.0 coins", out)
        self.assertEqual(self.run_cli("validate")[0], 0)

        home = Path(self._tmp.name)
        self.assertTrue((home / "data" / "chain.json").exists())
        self.assertTrue((home / "wallets" / "alice.pem").exists())
        self.assertIn("Block 2 mined", (home / "logs" / "pychain.log").read_text())

    def test_unknown_wallet_returns_error(self):
        self.assertEqual(self.run_cli("mine", "ghost")[0], 1)

    def test_reset_requires_confirmation(self):
        self.assertEqual(self.run_cli("reset")[0], 1)


if __name__ == "__main__":
    unittest.main()
