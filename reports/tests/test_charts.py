"""Story 8.2 — SVG chart primitives unit tests.

Charts are pure functions — given the same data they always return the same
markup. Tests pin: presence of required a11y attributes, empty-input handling,
clickable wrapping, and that the donut total appears in the SVG.
"""

from decimal import Decimal

from reports.charts import BarPoint, PieSlice, svg_bar, svg_pie


def test_pie_empty_renders_placeholder() -> None:
    svg = svg_pie([])
    assert "<svg" in svg
    assert 'role="img"' in svg
    assert "Ma'lumot yo'q" in svg


def test_pie_renders_required_a11y_attrs() -> None:
    slices = [
        PieSlice(label="Taxi", value=Decimal("300")),
        PieSlice(label="Qahva", value=Decimal("100")),
    ]
    svg = svg_pie(slices, title="Test", desc="DescX")
    assert "<title>Test</title>" in svg
    assert "<desc>DescX</desc>" in svg
    assert 'role="img"' in svg
    assert 'aria-label="Test"' in svg


def test_pie_slice_with_href_is_wrapped_in_anchor() -> None:
    slices = [PieSlice(label="Taxi", value=Decimal("300"), href="/app/transactions/history/")]
    svg = svg_pie(slices)
    assert '<a xlink:href="/app/transactions/history/"' in svg


def test_pie_centre_total_rendered() -> None:
    slices = [
        PieSlice(label="A", value=Decimal("500")),
        PieSlice(label="B", value=Decimal("1500")),
    ]
    svg = svg_pie(slices)
    # 2000 -> "2k"
    assert ">2k<" in svg or ">2.0k<" in svg


def test_pie_handles_zero_slices() -> None:
    """If every value is zero we get the placeholder branch."""
    slices = [PieSlice(label="A", value=Decimal("0"))]
    svg = svg_pie(slices)
    assert "Ma'lumot yo'q" in svg


def test_bar_empty_returns_placeholder() -> None:
    svg = svg_bar([])
    assert "Ma'lumot yo'q" in svg
    assert 'role="img"' in svg


def test_bar_renders_one_rect_per_point() -> None:
    points = [BarPoint(label="Du", value=Decimal("100")), BarPoint(label="Se", value=Decimal("0"))]
    svg = svg_bar(points, title="Daily")
    assert svg.count("<rect") == 2
    # Zero-value bar uses the muted stripe colour.
    assert "#e2e8f0" in svg


def test_bar_highlight_uses_amber() -> None:
    points = [
        BarPoint(label="Yan", value=Decimal("100")),
        BarPoint(label="Fev", value=Decimal("200")),
    ]
    svg = svg_bar(points, highlight_index=1, color="#10b981")
    # Amber accent applied to the highlighted bar.
    assert "#f59e0b" in svg


def test_bar_labels_rendered() -> None:
    points = [
        BarPoint(label="Du", value=Decimal("100")),
        BarPoint(label="Se", value=Decimal("200")),
    ]
    svg = svg_bar(points)
    assert ">Du<" in svg
    assert ">Se<" in svg
