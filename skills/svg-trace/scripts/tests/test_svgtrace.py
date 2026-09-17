import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import svgtrace as st  # noqa: E402


def test_no_subcommand_exits_2():
    with pytest.raises(SystemExit) as exc:
        st.main([])
    assert exc.value.code == 2


def test_error_is_reported_without_traceback(capsys, monkeypatch):
    def boom(args):
        raise st.SvgTraceError("測試用錯誤")

    monkeypatch.setattr(st, "_dispatch", boom)
    code = st.main(["palette", "x.png"])
    assert code == 1
    assert "測試用錯誤" in capsys.readouterr().err
