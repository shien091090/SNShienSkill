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


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_svg_size_from_viewbox(tmp_path):
    p = _write(tmp_path, "a.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1184 666"/>')
    assert st.svg_size_px(p) == (1184.0, 666.0)


def test_svg_size_falls_back_to_width_height(tmp_path):
    p = _write(tmp_path, "b.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320"/>')
    assert st.svg_size_px(p) == (640.0, 320.0)


def test_svg_size_strips_units(tmp_path):
    p = _write(tmp_path, "c.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="640px" height="320px"/>')
    assert st.svg_size_px(p) == (640.0, 320.0)


def test_svg_size_without_any_size_raises(tmp_path):
    p = _write(tmp_path, "d.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
    with pytest.raises(st.SvgTraceError, match="viewBox"):
        st.svg_size_px(p)


def test_svg_size_parse_error_raises(tmp_path):
    p = _write(tmp_path, "e.svg", "<svg><unclosed>")
    with pytest.raises(st.SvgTraceError, match="解析失敗"):
        st.svg_size_px(p)


def test_svg_size_missing_file_raises(tmp_path):
    with pytest.raises(st.SvgTraceError, match="檔案不存在"):
        st.svg_size_px(tmp_path / "nope.svg")


def test_fit_box_height_limited():
    # 1184x666 塞進 12.333 x 6.5 吋: 高度先撞牆, 高吃滿 6.5, 寬按比例縮並水平置中
    x, y, w, h = st.fit_box(1184, 666, (0.5, 0.5, 12.333, 6.5))
    assert h == pytest.approx(6.5)
    assert w == pytest.approx(11.5556, abs=0.001)
    assert x == pytest.approx(0.8887, abs=0.001)
    assert y == pytest.approx(0.5)


def test_fit_box_width_limited():
    # 1184x400 塞進同一個 box: 寬度先撞牆, 寬吃滿 12.333, 高按比例縮並垂直置中
    x, y, w, h = st.fit_box(1184, 400, (0.5, 0.5, 12.333, 6.5))
    assert w == pytest.approx(12.333, abs=0.001)
    assert h == pytest.approx(4.1667, abs=0.001)
    assert x == pytest.approx(0.5)
    assert y == pytest.approx(1.6667, abs=0.001)


def test_svg_size_viewbox_token_count_wrong(tmp_path):
    p = _write(tmp_path, "f.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100"/>')
    with pytest.raises(st.SvgTraceError, match="viewBox"):
        st.svg_size_px(p)


def test_svg_size_viewbox_contains_non_numeric(tmp_path):
    p = _write(tmp_path, "g.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 abc 666"/>')
    with pytest.raises(st.SvgTraceError, match="viewBox"):
        st.svg_size_px(p)


def test_svg_size_invalid_width_value(tmp_path):
    p = _write(tmp_path, "h.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="abc" height="10"/>')
    with pytest.raises(st.SvgTraceError, match="width.*無效"):
        st.svg_size_px(p)


def test_svg_size_invalid_height_value(tmp_path):
    p = _write(tmp_path, "i.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="xyz"/>')
    with pytest.raises(st.SvgTraceError, match="height.*無效"):
        st.svg_size_px(p)
