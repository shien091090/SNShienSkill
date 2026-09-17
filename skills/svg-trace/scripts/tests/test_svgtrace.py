import re
import sys
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Inches

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


SVG_OK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
  <rect x="10" y="10" width="100" height="50" fill="#2B579A"/>
  <text x="20" y="40" font-size="16" fill="#FFFFFF">框</text>
</svg>'''


def test_svg_problems_empty_for_supported_svg(tmp_path):
    p = _write(tmp_path, "ok.svg", SVG_OK)
    assert st.svg_problems(p) == []


def test_svg_problems_reports_unsupported_element(tmp_path):
    p = _write(tmp_path, "bad.svg",
               '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
               '<foreignObject width="1" height="1"/></svg>')
    problems = st.svg_problems(p)
    assert len(problems) == 1
    assert "foreignObject" in problems[0]


def test_svg_problems_reports_parse_error(tmp_path):
    p = _write(tmp_path, "broken.svg", "<svg><unclosed>")
    assert any("解析失敗" in m for m in st.svg_problems(p))


def test_svg_problems_missing_file(tmp_path):
    p = tmp_path / "nonexistent.svg"
    problems = st.svg_problems(p)
    assert len(problems) == 1
    assert "檔案不存在" in problems[0]


def test_build_creates_16_9_deck_when_missing(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out)
    prs = Presentation(str(out))
    assert prs.slide_width == Inches(13.333)
    assert prs.slide_height == Inches(7.5)
    assert len(prs.slides._sldIdLst) == 1


def test_build_appends_a_slide_to_existing_deck(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out, name="第一張")
    st.build(svg, out, name="第二張")
    slides = list(Presentation(str(out)).slides)
    assert len(slides) == 2
    # 原有那頁不可被動到
    assert [s.shapes[0].name for s in slides] == ["第一張", "第二張"]


def test_build_keeps_existing_slide_size(tmp_path):
    out = tmp_path / "four-three.pptx"
    Presentation().save(str(out))  # python-pptx 預設 10 x 7.5 吋
    svg = _write(tmp_path, "d.svg", SVG_OK)
    st.build(svg, out)
    after = Presentation(str(out))
    assert after.slide_width == Inches(10)
    assert after.slide_height == Inches(7.5)


def test_build_slide_has_only_the_diagram_group(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out, name="流程")
    slide = list(Presentation(str(out)).slides)[0]
    assert len(slide.shapes) == 1
    assert slide.shapes[0].name == "流程"


def test_build_shape_ids_do_not_collide(tmp_path):
    svg = _write(tmp_path, "d.svg", SVG_OK)
    out = tmp_path / "out.pptx"
    st.build(svg, out)
    st.build(svg, out)
    for slide in Presentation(str(out)).slides:
        ids = re.findall(r'<p:cNvPr id="(\d+)"', slide.shapes._spTree.xml)
        assert len(ids) == len(set(ids)), "同一頁裡的圖案編號重複了"


def test_build_refuses_unsupported_svg(tmp_path):
    svg = _write(tmp_path, "bad2.svg",
                 '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                 '<foreignObject width="1" height="1"/></svg>')
    with pytest.raises(st.SvgTraceError, match="foreignObject"):
        st.build(svg, tmp_path / "x.pptx")
    assert not (tmp_path / "x.pptx").exists(), "驗證沒過就不該產出半成品"


def test_build_reports_locked_file_in_chinese(tmp_path, monkeypatch):
    svg = _write(tmp_path, "d.svg", SVG_OK)

    def deny(self, path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("pptx.presentation.Presentation.save", deny)
    with pytest.raises(st.SvgTraceError, match="PowerPoint"):
        st.build(svg, tmp_path / "locked.pptx")


def test_svg_problems_reports_count_when_exceeds_limit(tmp_path):
    # 造 9 個 foreignObject, 超過 8 個上限
    svg_with_many = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <foreignObject x="0" y="0" width="10" height="10"/>
      <foreignObject x="10" y="0" width="10" height="10"/>
      <foreignObject x="20" y="0" width="10" height="10"/>
      <foreignObject x="30" y="0" width="10" height="10"/>
      <foreignObject x="40" y="0" width="10" height="10"/>
      <foreignObject x="50" y="0" width="10" height="10"/>
      <foreignObject x="60" y="0" width="10" height="10"/>
      <foreignObject x="70" y="0" width="10" height="10"/>
      <foreignObject x="80" y="0" width="10" height="10"/>
    </svg>'''
    p = _write(tmp_path, "many.svg", svg_with_many)
    problems = st.svg_problems(p)
    assert len(problems) == 1
    assert "foreignObject" in problems[0]
    assert "還有 1 個" in problems[0]
