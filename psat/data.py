"""Du lieu tra cuu: ong, vat lieu, moi chat, bao on, tieu chuan.

CANH BAO QUAN TRONG
-------------------
Cac bang duoi day la DU LIEU THAM KHAO de dien nhanh. Chung KHONG thay the
tieu chuan goc. Truoc khi dung cho thiet ke phat hanh, phai doi chieu:

    kich thuoc ong      ASME B36.10M (thep carbon) / B36.19M (thep khong gi)
    ung suat cho phep   ASME B31.3 Bang A-1 / A-2 tai NHIET DO THIET KE
    thep ket cau        catalogue nha san xuat + tieu chuan vat lieu

Moi o nhap trong chuong trinh deu cho phep GHI DE bang tay. Neu ban khong
chac mot gia tri, hay nhap gia tri lay tu tai lieu cua du an.
"""

from __future__ import annotations

DISCLAIMER = (
    "Du lieu tra cuu chi de dien nhanh - phai doi chieu ASME B36.10M/B36.19M, "
    "B31.3 Bang A-1 va catalogue nha san xuat truoc khi phat hanh thiet ke."
)

# --------------------------------------------------------------------------
# Tieu chuan lien quan
# --------------------------------------------------------------------------
STANDARDS = {
    "LNG / NG - nha may, cong nghe": [
        ("ASME B31.3", "Process Piping - bo tieu chuan duong ong cong nghe pho bien nhat cho nha may LNG"),
        ("ASME B31.3 App. M", "Huong dan chon bo tieu chuan phu hop"),
        ("EN 1473", "Installation and equipment for LNG - thiet ke tren bo"),
        ("NFPA 59A", "Production, storage and handling of LNG"),
        ("EN 13480", "Metallic industrial piping (he chau Au)"),
    ],
    "NG - tuyen ong dan, phan phoi": [
        ("ASME B31.8", "Gas Transmission and Distribution Piping Systems"),
        ("ASME B31.8S", "Managing System Integrity of Gas Pipelines"),
        ("API 5L", "Line Pipe"),
    ],
    "Gia do / support": [
        ("MSS SP-58", "Pipe Hangers and Supports - vat lieu, thiet ke, che tao"),
        ("MSS SP-69", "Pipe Hangers and Supports - lua chon va ung dung"),
        ("ASME B31.3 para. 321", "Yeu cau ve gia do trong B31.3"),
        ("ASME B31.1 Table 121.5", "Khoang cach gia do goi y (co so: sigma_b 15.9 MPa, vong 2.5 mm)"),
        ("AISC 360", "Specification for Structural Steel Buildings - kiem tra thanh thep"),
        ("EN 1993-1-1", "Eurocode 3 - thiet ke ket cau thep"),
    ],
    "Hoi/nuoc, cong dung chung": [
        ("ASME B31.1", "Power Piping"),
        ("TCVN 6155/6156", "Binh chiu ap luc - yeu cau ky thuat an toan"),
    ],
}

DEFAULT_STANDARD = "ASME B31.3"


# --------------------------------------------------------------------------
# Kich thuoc ong - ASME B36.10M / B36.19M (trich)
#   NPS : (OD mm, { schedule : wall mm })
# --------------------------------------------------------------------------
PIPE_OD = {
    '1/2': 21.3, '3/4': 26.7, '1': 33.4, '1-1/4': 42.2, '1-1/2': 48.3,
    '2': 60.3, '2-1/2': 73.0, '3': 88.9, '4': 114.3, '5': 141.3,
    '6': 168.3, '8': 219.1, '10': 273.0, '12': 323.8, '14': 355.6,
    '16': 406.4, '18': 457.2, '20': 508.0, '24': 609.6,
}

PIPE_DN = {
    '1/2': 'DN15', '3/4': 'DN20', '1': 'DN25', '1-1/4': 'DN32',
    '1-1/2': 'DN40', '2': 'DN50', '2-1/2': 'DN65', '3': 'DN80',
    '4': 'DN100', '5': 'DN125', '6': 'DN150', '8': 'DN200',
    '10': 'DN250', '12': 'DN300', '14': 'DN350', '16': 'DN400',
    '18': 'DN450', '20': 'DN500', '24': 'DN600',
}

# chieu day thanh [mm]
PIPE_WALL = {
    #        Sch10S  Sch40/STD  Sch80/XS   Sch160
    '1/2':    {'10S': 2.11, '40 (STD)': 2.77,  '80 (XS)': 3.73,  '160': 4.78},
    '3/4':    {'10S': 2.11, '40 (STD)': 2.87,  '80 (XS)': 3.91,  '160': 5.56},
    '1':      {'10S': 2.77, '40 (STD)': 3.38,  '80 (XS)': 4.55,  '160': 6.35},
    '1-1/4':  {'10S': 2.77, '40 (STD)': 3.56,  '80 (XS)': 4.85,  '160': 6.35},
    '1-1/2':  {'10S': 2.77, '40 (STD)': 3.68,  '80 (XS)': 5.08,  '160': 7.14},
    '2':      {'10S': 2.77, '40 (STD)': 3.91,  '80 (XS)': 5.54,  '160': 8.74},
    '2-1/2':  {'10S': 3.05, '40 (STD)': 5.16,  '80 (XS)': 7.01,  '160': 9.53},
    '3':      {'10S': 3.05, '40 (STD)': 5.49,  '80 (XS)': 7.62,  '160': 11.13},
    '4':      {'10S': 3.05, '40 (STD)': 6.02,  '80 (XS)': 8.56,  '160': 13.49},
    '5':      {'10S': 3.40, '40 (STD)': 6.55,  '80 (XS)': 9.53,  '160': 15.88},
    '6':      {'10S': 3.40, '40 (STD)': 7.11,  '80 (XS)': 10.97, '160': 18.26},
    '8':      {'10S': 3.76, '40 (STD)': 8.18,  '80 (XS)': 12.70, '160': 23.01},
    '10':     {'10S': 4.19, '40 (STD)': 9.27,  '80 (XS)': 15.09, '160': 28.58},
    '12':     {'10S': 4.57, 'STD': 9.53, '40': 10.31, 'XS': 12.70, '80': 17.48},
    '14':     {'10S': 4.78, 'STD': 9.53, '40': 11.13, 'XS': 12.70, '80': 19.05},
    '16':     {'10S': 4.78, 'STD': 9.53, '40': 12.70, 'XS': 12.70, '80': 21.44},
    '18':     {'10S': 4.78, 'STD': 9.53, '40': 14.27, 'XS': 12.70, '80': 23.83},
    '20':     {'10S': 5.54, 'STD': 9.53, '40': 15.09, 'XS': 12.70, '80': 26.19},
    '24':     {'10S': 6.35, 'STD': 9.53, '40': 17.48, 'XS': 12.70, '80': 30.96},
}


def schedules_for(nps: str) -> list[str]:
    return list(PIPE_WALL.get(nps, {}).keys())


# --------------------------------------------------------------------------
# Vat lieu ong
#   ten : (rho kg/m3, E MPa o nhiet do thuong, ghi chu ve pham vi nhiet do)
# --------------------------------------------------------------------------
PIPE_MATERIALS = {
    "A106 Gr.B (thep carbon)": (
        7850, 203000,
        "Duong ong cong nghe thong thuong. KHONG dung cho nhiet do am sau "
        "(gioi han thuong -29 C) - khong phu hop LNG."),
    "A333 Gr.6 (thep nhiet do thap)": (
        7850, 203000,
        "Thep chiu lanh, thuong dung den -45 C. Dung cho NG lanh, "
        "KHONG du cho LNG -162 C."),
    "A333 Gr.3 (3.5% Ni)": (
        7850, 203000,
        "Den khoang -101 C. Van chua du cho LNG -162 C."),
    "A333 Gr.8 / A353 (9% Ni)": (
        7850, 200000,
        "9% Ni - vat lieu kinh dien cho LNG den -196 C."),
    "A312 TP304 / 304L (inox austenit)": (
        8000, 193000,
        "Austenit - dung tot den -196 C. Lua chon pho bien cho ong LNG."),
    "A312 TP316 / 316L (inox austenit)": (
        8000, 193000,
        "Nhu 304 nhung chong an mon tot hon (moi truong bien)."),
    "API 5L X52 (tuyen ong)": (
        7850, 207000,
        "Tuyen ong dan khi. Theo ASME B31.8."),
    "API 5L X60 / X65 (tuyen ong)": (
        7850, 207000,
        "Tuyen ong dan khi ap suat cao."),
    "Nhom 5083": (
        2660, 71000,
        "Nhom hop kim - dung duoc den -196 C, nhe, nhung E chi bang 1/3 thep "
        "nen do vong lon hon nhieu."),
}

LNG_SUITABLE = (
    "A333 Gr.8 / A353 (9% Ni)",
    "A312 TP304 / 304L (inox austenit)",
    "A312 TP316 / 316L (inox austenit)",
    "Nhom 5083",
)


# --------------------------------------------------------------------------
# Moi chat trong ong  -  ten : (rho kg/m3, ghi chu)
# --------------------------------------------------------------------------
FLUIDS = {
    "LNG (long, -162 C)":        (450.0, "Thuong 430-470 tuy thanh phan."),
    "NG (khi, ap suat thap)":    (0.8,   "Gan nhu khong dang ke so voi ong."),
    "NG (khi, 10 barg)":         (8.0,   "Uoc luong - nen tinh lai theo P, T thuc te."),
    "NG (khi, 50 barg)":         (40.0,  "Uoc luong - nen tinh lai theo P, T thuc te."),
    "Nuoc (thuy luc / test)":    (1000.0, "Truong hop THU THUY LUC - thuong la to hop nang nhat."),
    "Dau nhe":                   (850.0, ""),
    "Khong khi / nito":          (1.2,   ""),
    "Rong (khong co moi chat)":  (0.0,   ""),
}

DEFAULT_FLUID = "LNG (long, -162 C)"


# --------------------------------------------------------------------------
# Bao on  -  ten : (rho kg/m3, ghi chu)
# --------------------------------------------------------------------------
INSULATION = {
    "Khong bao on":                 (0.0,   ""),
    "PIR / PUR foam":               (45.0,  "Cach nhiet lanh pho bien."),
    "Cellular glass (Foamglas)":    (120.0, "Dung nhieu cho cryogenic, chiu nen tot - "
                                            "thuong dung lam GOI DO lanh."),
    "Bong khoang (mineral wool)":   (100.0, "Cho duong nong."),
    "Perlite":                      (60.0,  ""),
}


# --------------------------------------------------------------------------
# Thep lam gia do  -  ten : (Fy MPa, Fu MPa, E MPa, rho kg/m3, ghi chu)
# --------------------------------------------------------------------------
SUPPORT_STEEL = {
    "S235 / CT3 / SS400":        (235.0, 360.0, 210000.0, 7850.0, "Thep ket cau thong dung."),
    "S275":                      (275.0, 430.0, 210000.0, 7850.0, ""),
    "S355 / Q345":               (355.0, 490.0, 210000.0, 7850.0, "Cuong do cao hon."),
    "ASTM A36":                  (250.0, 400.0, 200000.0, 7850.0, "He My."),
    "ASTM A992 (W-shape)":       (345.0, 450.0, 200000.0, 7850.0, "Thep hinh ket cau My."),
    "ASTM A500 Gr.B (hop)":      (315.0, 400.0, 200000.0, 7850.0, "Thep hop HSS."),
    "SUS304 (inox)":             (205.0, 515.0, 193000.0, 8000.0,
                                  "Dung khi gia do tiep xuc truc tiep moi truong lanh/an mon."),
}

DEFAULT_STEEL = "S235 / CT3 / SS400"

# He so an toan (ASD). 1.67 tuong ung 0.6*Fy cho keo/uon theo AISC.
DEFAULT_SF = 1.67

GRAVITY = 9.80665           # m/s2
