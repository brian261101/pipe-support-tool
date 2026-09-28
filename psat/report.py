# -*- coding: utf-8 -*-
"""Xuất báo cáo tính toán dạng văn bản."""

from __future__ import annotations

import datetime

from .analysis import Project, Result
from .checks import SF
from .data import DISCLAIMER

LINE = "=" * 78
THIN = "-" * 78


def _h(t: str) -> str:
    return "\n%s\n%s\n%s\n" % (LINE, t, LINE)


def _s(t: str) -> str:
    return "\n%s\n%s\n" % (t, THIN)


def build(p: Project, r: Result, advice, pipe_info: str = "",
          section_info: str = "", title: str = "TÍNH TOÁN GIÁ ĐỠ ĐƯỜNG ỐNG") -> str:
    a = r.assessment
    out = []
    out.append(_h(title))
    out.append("Lập lúc : %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    out.append("Công cụ : Pipe Support Analysis Tool — PTHH khung phẳng\n")
    out.append("Phương pháp: phần tử dầm Euler-Bernoulli 2D, 6 bậc tự do;\n")
    out.append("             kiểm tra theo ứng suất cho phép (ASD), hệ số an toàn %.2f;\n" % SF)
    out.append("             ổn định tổng thể bằng bài toán trị riêng (K + lambda*Kg).\n")

    if pipe_info:
        out.append(_s("1. ĐƯỜNG ỐNG VÀ TẢI TRỌNG"))
        out.append(pipe_info)

    if section_info:
        out.append(_s("2. TIẾT DIỆN THÉP GIÁ ĐỠ"))
        out.append(section_info)

    out.append(_s("3. SƠ ĐỒ KẾT CẤU"))
    out.append("Vật liệu thép : Fy = %.0f MPa, E = %.0f MPa\n" % (p.Fy, p.E))
    out.append("Chia lưới     : %d phần tử trên mỗi thanh, tổng %d phần tử, %d nút\n"
               % (p.nseg, len(r.model.elements), len(r.model.nodes)))
    out.append("Hệ số chiều dài tính toán K = %.2f\n" % p.K_factor)
    out.append("Trọng lượng bản thân thanh: %s\n"
               % ("có kể" if p.self_weight else "bỏ qua"))
    out.append("\nThanh:\n")
    for i, m in enumerate(p.members):
        out.append("  %-10s (%8.1f,%8.1f) -> (%8.1f,%8.1f)  L=%8.1f mm  %s\n"
                   % (m.label or "T%d" % (i + 1), m.x1, m.y1, m.x2, m.y2,
                      m.length, m.section.name))
    out.append("\nGối tựa:\n")
    for i, s in enumerate(p.supports):
        out.append("  G%-9d (%8.1f,%8.1f)  %s\n" % (i + 1, s.x, s.y, s.kind))
    out.append("\nTải tác dụng:\n")
    for i, l in enumerate(p.loads):
        out.append("  %-10s (%8.1f,%8.1f)  %9.1f N  góc %6.1f do  "
                   "(Fx=%9.1f  Fy=%9.1f)\n"
                   % (l.label or "P%d" % (i + 1), l.x, l.y, l.magnitude,
                      l.angle, l.fx, l.fy))

    out.append(_s("4. NỘI LỰC VÀ KIỂM TRA THANH"))
    out.append("%-10s %-4s %11s %13s %10s %7s %7s %6s\n"
               % ("Thanh", "K/N", "N [N]", "M [N.mm]", "V [N]", "KL/r",
                  "fb[MPa]", "Dùng"))
    for c in a.members:
        out.append("%-10s %-4s %11.0f %13.4e %10.0f %7.1f %7.1f %5.0f%%\n"
                   % (c.name, c.action, c.N, c.M, c.V, c.slenderness,
                      c.fb, c.utilization * 100))
    out.append("\nChi tiết mặt cắt nguy hiểm:\n")
    for c in a.members:
        out.append("  %-10s x = %8.1f mm dọc thanh  -> toạ độ (%.1f, %.1f)\n"
                   % (c.name, c.x_crit, c.xy_crit[0], c.xy_crit[1]))
        out.append("             fa=%7.1f/Fa=%7.1f   fb=%7.1f/Fb=%7.1f   "
                   "fv=%7.1f/Fv=%7.1f\n"
                   % (c.fa, c.Fa, c.fb, c.Fb, c.fv, c.Fv))
        out.append("             tổ hợp AISC H1-1 = %.3f\n" % c.u_combined)

    out.append(_s("5. KẾT LUẬN"))
    out.append("Hệ số tải theo điều kiện BỀN        lambda_s  = %.3f\n"
               % a.lambda_strength)
    if a.lambda_buckling > 0:
        out.append("Hệ số tải tới hạn theo ỔN ĐỊNH      lambda_cr = %.3f\n"
                   % a.lambda_buckling)
        out.append("  (chia hệ số an toàn %.2f -> %.3f)\n"
                   % (SF, a.lambda_buckling / SF))
    else:
        out.append("Ổn định tổng thể: %s\n" % (a.buckling_note or "không xét"))
    out.append("HỆ SỐ TẢI CHO PHÉP                 lambda    = %.3f\n" % a.lambda_allow)
    out.append("Quyết định bởi                     %s\n" % a.governed_by)

    tot = sum(l.magnitude for l in p.loads)
    out.append("\nTải đang xét       = %10.1f N = %7.2f kN\n" % (tot, tot / 1000))
    out.append("TẢI TỐI ĐA CHỊU    = %10.1f N = %7.2f kN\n"
               % (tot * a.lambda_allow, tot * a.lambda_allow / 1000))
    out.append("\nChuyển vị lớn nhất = %.2f mm tại nút %d%s\n"
               % (a.max_disp, a.max_disp_node,
                  ("  (giới hạn %.1f mm - %s)"
                   % (a.disp_limit, "ĐẠT" if a.disp_ok else "VƯỢT"))
                  if a.disp_limit > 0 else ""))
    out.append("\nKẾT LUẬN: %s\n"
               % ("ĐẠT" if a.lambda_allow >= 1.0 and a.disp_ok else "KHÔNG ĐẠT"))

    if advice:
        out.append(_s("6. NHẬN XÉT VÀ ĐỀ XUẤT"))
        mark = {"!": "[QUAN TRỌNG]", "*": "[LƯU Ý]     ", "-": "[thông tin] "}
        for lv, t, s in advice:
            out.append("%s %s\n" % (mark.get(lv, "            "), t))
            if s:
                for chunk in _wrap(s, 74):
                    out.append("             %s\n" % chunk)
            out.append("\n")

    if r.notes:
        out.append(_s("7. GHI CHÚ TỪ CHƯƠNG TRÌNH"))
        for n in r.notes:
            for chunk in _wrap(n, 76):
                out.append("  %s\n" % chunk)

    out.append(_s("GIỚI HẠN CỦA KẾT QUẢ"))
    out.append(_para(
        "Mô hình là KHUNG PHẲNG 2D, nút cứng (hàn). Không xét: xoắn, ổn định "
        "ngang của dầm (LTB), ổn định cục bộ của bản thành, mỏi, tải trọng "
        "động và rung, động đất, gió, và liên kết bu-lông / mối hàn. Tiết "
        "diện coi là đặc chắc.", 76))
    out.append(_para(
        "Kiểm tra theo ứng suất cho phép với Fb = 0,6*Fy, không cộng thêm dự "
        "trữ dẻo - kết quả THIÊN VỀ AN TOÀN so với AISC 360 đầy đủ.", 76))
    out.append(_para(DISCLAIMER, 76))
    out.append(_para(
        "Kết quả này là công cụ SÀNG LỌC và định cỡ sơ bộ. Hồ sơ thiết kế "
        "phát hành phải được kỹ sư có thẩm quyền kiểm tra độc lập.", 76))
    return "".join(out)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return lines


def _para(text: str, width: int) -> str:
    return "".join("  %s\n" % l for l in _wrap(text, width)) + "\n"
