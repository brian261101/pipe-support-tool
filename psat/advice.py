# -*- coding: utf-8 -*-
"""Đề xuất kỹ thuật, suy ra từ chính kết quả phần tử hữu hạn.

Mỗi đề xuất đều gắn với một con số lấy từ kết quả tính — không có lời khuyên
chung chung. Điều kiện nào không xảy ra thì đề xuất tương ứng không hiện.
"""

from __future__ import annotations

from .analysis import Project, Result
from .checks import SF


def _hi(t, s):
    return ("!", t, s)


def _mid(t, s):
    return ("*", t, s)


def _info(t, s):
    return ("-", t, s)


def geometry_notes(p: Project) -> list[tuple[str, str, str]]:
    """Nhận dạng sơ đồ kết cấu từ hình học."""
    out = []
    nsup = len(p.supports)

    xs = [c for m in p.members for c in (m.x1, m.x2)]
    ys = [c for m in p.members for c in (m.y1, m.y2)]
    span_x = max(xs) - min(xs) if xs else 0.0
    span_y = max(ys) - min(ys) if ys else 0.0

    diag = [m for m in p.members
            if abs(m.x2 - m.x1) > 1.0 and abs(m.y2 - m.y1) > 1.0]

    if nsup == 1 and not diag:
        out.append(_hi(
            "Sơ đồ hiện tại là CÔNG XÔN không giằng",
            "Chỉ có 1 gối tựa và không có thanh chéo nào. Toàn bộ tải phải "
            "truyền về gối bằng UỐN — cách truyền lực kém hiệu quả nhất. "
            "Thêm một thanh chéo sẽ đổi phần lớn uốn thành lực dọc trục. "
            "Dạng phù hợp: giá đỡ công xôn có thanh chống chéo (cantilever "
            "bracket with diagonal brace)."))
    elif nsup == 1 and diag:
        out.append(_info(
            "Sơ đồ: công xôn CÓ giằng chéo",
            "Đã có %d thanh chéo. Đây là cấu hình đúng cho giá đỡ kiểu "
            "console / bracket gắn vào cột hoặc tường." % len(diag)))
    elif nsup >= 2 and span_x > 1.0:
        out.append(_info(
            "Sơ đồ: khung nhiều gối (kiểu khung cổng / goal post)",
            "%d gối tựa cách nhau %.0f mm. Khung dạng này chịu tải tốt hơn "
            "nhiều so với công xôn và là lựa chọn tiêu chuẩn khi ống chạy "
            "giữa hai cột." % (nsup, span_x)))

    if span_y > 3000 and nsup <= 2 and not diag:
        out.append(_mid(
            "Cột cao %.0f mm không có giằng" % span_y,
            "Cột cao và không giằng rất nhạy với mất ổn định và chuyển vị "
            "ngang. Cân nhắc giằng chéo theo phương dọc tuyến ống, hoặc "
            "chuyển sang khung chữ A."))
    return out


def result_advice(p: Project, r: Result) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    a = r.assessment
    gov = a.governing

    if a.lambda_allow >= 1.0:
        out.append(_info(
            "ĐẠT — hệ số dư tải %.2f" % a.lambda_allow,
            "Kết cấu chịu được tải hiện tại. Còn có thể tăng tải thêm %.0f%% "
            "trước khi chạm giới hạn (%s)."
            % ((a.lambda_allow - 1.0) * 100.0, a.governed_by)))
    else:
        out.append(_hi(
            "KHÔNG ĐẠT — chỉ đạt %.0f%% tải yêu cầu" % (a.lambda_allow * 100.0),
            "Phải tăng tiết diện, đổi sơ đồ, hoặc giảm nhịp ống. "
            "Yếu tố quyết định: %s." % a.governed_by))

    if gov is not None and gov.dominant == "uốn" and gov.u_bend > 0.35:
        out.append(_mid(
            "Uốn chi phối %s — nên chuyển sang sơ đồ có giằng" % gov.name,
            "Ứng suất uốn %.0f MPa chiếm %.0f%% khả năng, trong khi dọc trục "
            "chỉ %.0f MPa. Một thanh chéo đặt từ gối đến gần điểm đặt lực sẽ "
            "biến phần lớn moment này thành lực dọc trục — thường tăng được "
            "3–8 lần khả năng chịu tải mà không cần đổi tiết diện."
            % (gov.fb, gov.u_bend * 100.0, gov.fa)))

    for c in a.members:
        if c.action == "NÉN" and c.slenderness > 120:
            out.append(_mid(
                "%s mảnh (KL/r = %.0f)" % (c.name, c.slenderness),
                "Khả năng chịu nén chỉ còn Fa = %.0f MPa so với 0,6·Fy = "
                "%.0f MPa — mất %.0f%%. Xử lý theo thứ tự hiệu quả: (1) giằng "
                "giữa thanh để giảm chiều dài tính toán, (2) đổi sang tiết "
                "diện KÍN (hộp hoặc ống) vì cùng diện tích thì r lớn hơn thép "
                "góc rất nhiều, (3) cuối cùng mới tăng kích thước."
                % (c.Fa, 0.6 * p.Fy, (1 - c.Fa / (0.6 * p.Fy)) * 100.0)))

    if a.lambda_buckling > 0:
        if a.lambda_buckling < SF:
            out.append(_hi(
                "Mất ổn định tổng thể trước khi đạt giới hạn bền",
                "Hệ số tải tới hạn λ_cr = %.2f < hệ số an toàn %.2f. Kết cấu "
                "sẽ mất ổn định ở %.0f%% tải hiện tại. Bắt buộc phải giằng."
                % (a.lambda_buckling, SF, a.lambda_buckling * 100.0)))
        elif a.lambda_buckling < 4.0:
            out.append(_mid(
                "Ổn định tổng thể cần lưu ý (λ_cr = %.2f)" % a.lambda_buckling,
                "Dưới 4 thì hiệu ứng bậc hai (P-delta) bắt đầu đáng kể. Nếu "
                "làm thiết kế chính thức nên phân tích phi tuyến hình học "
                "hoặc dùng công thức khuếch đại moment."))
        else:
            out.append(_info(
                "Ổn định tổng thể tốt (λ_cr = %.1f)" % a.lambda_buckling,
                "Kết cấu còn xa ngưỡng mất ổn định đàn hồi."))

    if a.disp_limit > 0:
        if a.max_disp > a.disp_limit:
            out.append(_hi(
                "Chuyển vị %.1f mm vượt giới hạn %.1f mm"
                % (a.max_disp, a.disp_limit),
                "Độ cứng uốn tỉ lệ với I, mà I tỉ lệ với chiều cao mũ ba. "
                "Tăng CHIỀU CAO tiết diện hiệu quả hơn nhiều so với tăng bề dày."))
        else:
            out.append(_info(
                "Chuyển vị %.1f mm / giới hạn %.1f mm — đạt"
                % (a.max_disp, a.disp_limit), ""))
    else:
        out.append(_info("Chuyển vị lớn nhất %.1f mm" % a.max_disp,
                         "Chưa đặt giới hạn chuyển vị để kiểm tra."))

    if gov is not None and gov.utilization < 0.35 and a.lambda_buckling > 6:
        out.append(_info(
            "Tiết diện còn dư nhiều (dùng %.0f%%)" % (gov.utilization * 100.0),
            "Có thể giảm kích thước để tiết kiệm. Dùng nút 'Tự chọn tiết diện' "
            "để tìm phương án nhẹ nhất còn đạt."))

    for c in a.members:
        for w in c.warnings:
            out.append(_mid(c.name, w))

    return out


def sizing_advice(p: Project, r: Result) -> list[tuple[str, str, str]]:
    """Kích thước tối thiểu cần thiết, suy từ nội lực hiện tại."""
    out = []
    for c in r.assessment.members:
        if c.utilization <= 1.0:
            continue
        need = []
        if c.u_bend > 0 and c.fb > 0:
            S_now = abs(c.M) / c.fb
            need.append("Sx ≥ %.3e mm³ (đang có %.3e — thiếu %.0f%%)"
                        % (abs(c.M) / (0.6 * p.Fy), S_now,
                           (abs(c.M) / (0.6 * p.Fy) / S_now - 1) * 100))
        if c.u_axial > 0 and c.Fa > 0:
            need.append("A ≥ %.0f mm²" % (abs(c.N) / c.Fa))
        out.append(_hi(
            "%s cần tăng tiết diện (đang dùng %.0f%%)"
            % (c.name, c.utilization * 100.0),
            "Ước lượng bậc một: " + "; ".join(need) +
            ". Vì khung siêu tĩnh sẽ phân bố lại nội lực khi đổi tiết diện, "
            "hãy dùng 'Tự chọn tiết diện' để xác nhận."))
    return out


def cryogenic_notes(fluid: str, material: str, dT: float,
                    run_length_m: float) -> list[tuple[str, str, str]]:
    """Lưu ý riêng cho đường ống lạnh sâu — phần dễ bị bỏ qua nhất."""
    out = []
    if "LNG" not in fluid and dT > -50:
        return out

    from .pipe import THERMAL_ALPHA
    if "304" in material or "316" in material:
        alpha, mat = THERMAL_ALPHA["Inox austenit"], "inox austenit"
    elif "Ni" in material:
        alpha, mat = THERMAL_ALPHA["Thep 9% Ni"], "thép 9% Ni"
    elif "hôm" in material or "hom" in material:
        alpha, mat = THERMAL_ALPHA["Nhôm"], "nhôm"
    else:
        alpha, mat = THERMAL_ALPHA["Thep carbon"], "thép carbon"
    move = abs(alpha * dT * run_length_m * 1000.0)

    out.append(_hi(
        "Co ngót vì lạnh: %.0f mm trên %.0f m tuyến" % (move, run_length_m),
        "Với ΔT = %.0f °C và hệ số giãn nở %.2e/°C của %s, đoạn ống dài %.0f m "
        "sẽ CO khoảng %.0f mm. Gối đỡ phải cho phép chuyển vị này: dùng gối "
        "TRƯỢT hoặc CON LĂN, không ngàm cứng. Nếu chặn cứng, lực sinh ra có "
        "thể lớn gấp nhiều lần tải trọng lượng và sẽ phá hỏng cả giá đỡ lẫn ống."
        % (dT, alpha, mat, run_length_m, move)))

    out.append(_hi(
        "Cầu nhiệt (cold bridge) tại vị trí gối đỡ",
        "Giá đỡ thép tiếp xúc trực tiếp ống lạnh sẽ dẫn nhiệt ra ngoài, gây "
        "đóng băng và làm thép giá đỡ giòn. Phải dùng GỐI ĐỠ LẠNH (cold shoe) "
        "với đệm chịu nén cách nhiệt — thường là cellular glass hoặc gỗ cứng "
        "tẩm — để ngăn tiếp xúc trực tiếp."))

    out.append(_mid(
        "Vật liệu giá đỡ ở vùng có thể bị lạnh",
        "Thép carbon thông thường trở nên giòn ở nhiệt độ thấp. Phần giá đỡ có "
        "khả năng xuống dưới −29 °C phải dùng vật liệu chịu lạnh (inox "
        "austenit, hoặc thép có chứng nhận thử va đập ở nhiệt độ thiết kế)."))
    return out


def all_advice(p: Project, r: Result, fluid: str = "", material: str = "",
               dT: float = 0.0, run_length_m: float = 0.0):
    out = []
    out += result_advice(p, r)
    out += geometry_notes(p)
    out += sizing_advice(p, r)
    if fluid or dT:
        out += cryogenic_notes(fluid, material, dT, run_length_m)
    rank = {"!": 0, "*": 1, "-": 2}
    out.sort(key=lambda t: rank.get(t[0], 3))
    return out
