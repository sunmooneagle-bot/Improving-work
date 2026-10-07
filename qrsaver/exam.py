"""검사의뢰서 QR 의 검사코드(처방코드) → 검사명, 검체 종류별로 목록 체크 칸 활성화.

새 QR 형식: '26C 054730;A;1;;FB0164;1'
  - 첫 칸 '26C 054730' = 검사번호 (기존과 같이 AMIS 조회에 사용)
  - 'A;1;' 등 나머지는 무시, 'FB0164' 처럼 영문 2자 + 숫자로 된 칸 = 검사코드
검사코드표는 프로그램 폴더의 '검사코드.xlsx' (A열 처방코드, B열 처방영문명) 가 있으면 그것을,
없으면 아래 내장 표를 사용한다.
"""
import os
import re
import xml.etree.ElementTree as ET
import zipfile

_CODE_RE = re.compile(r"^[A-Z]{2}\d{3,}$")


def parse_qr(text):
    """QR 문자열(한글 보정·대문자 처리 후) → (검사번호 부분, 검사코드 또는 '').
    ';' 가 없으면 예전 QR(검사번호만)로 보고 그대로 돌려준다."""
    text = (text or "").strip()
    if ";" not in text:
        return text, ""
    parts = [p.strip() for p in text.split(";")]
    code = next((p.upper() for p in parts[1:] if _CODE_RE.match(p.upper())), "")
    return parts[0], code


_NUM_RE = re.compile(r"^(\d{2})\s*([A-Za-z]{1,2})\s+(\d{3,})$")


def old_style_number(number):
    """새 QR 의 검사번호 '26C 054730' → 예전 QR 과 같은 모양 '26-C -054730'.
    (병리결과입력에 번호를 넣는 방식은 예전 QR 과 똑같이 유지하기 위함) 다른 모양이면 그대로."""
    m = _NUM_RE.match((number or "").strip())
    if not m:
        return number
    return "%s-%s -%s" % (m.group(1), m.group(2), m.group(3))


# 내장 검사코드표 (검사코드.xlsx 기준)
BUILTIN = {
    'FB0001': 'Adrenal gland (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0002': 'Adrenal gland (EUS guided FNA)(Des)[Smear]',
    'FB0005': 'Ampulla of vater (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0006': 'Ampulla of vater (EUS guided FNA)(Des)[Smear]',
    'FB0008': 'Ascitic fluid (Des)[Liquid based cytology]',
    'FB0010': 'Specimen labeled (EBUS guided TBNA)(Des)[Smear with cell block]',
    'FB0011': 'Specimen labeled (EBUS guided TBNA)(Des)[Smear]',
    'FB0012': 'Specimen labeled (CT guided PCNA)(Des)[Smear with cell block]',
    'FB0013': 'Specimen labeled (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0014': 'Specimen labeled (Fluoroscopy guided PCNA)(Des)[Smear with cell block]',
    'FB0015': 'Specimen labeled (US guided PCNA)(Des)[Smear with cell block]',
    'FB0016': 'Specimen labeled (CT guided PCNA)(Des)[Smear]',
    'FB0017': 'Specimen labeled (EUS guided FNA)(Des)[Smear]',
    'FB0018': 'Specimen labeled (Fluoroscopy guided PCNA)(Des)[Smear]',
    'FB0019': 'Specimen labeled (US guided PCNA)(Des)[Smear]',
    'FB0021': 'Bronchoalveolar lavage (Des)[Liquid based cytology]',
    'FB0022': 'Bile duct (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0023': 'Bile duct (EUS guided FNA)(Des)[Smear]',
    'FB0025': 'Bile (Des)[Liquid based cytology]',
    'FB0030': 'Specimen labeled (Des)[Liquid based cytology]',
    'FB0032': 'Bone (CT guided PCNA)(Des)[Smear with cell block]',
    'FB0033': 'Bone (US guided PCNA)(Des)[Smear with cell block]',
    'FB0034': 'Bone (CT guided PCNA)(Des)[Smear]',
    'FB0035': 'Bone (US guided PCNA)(Des)[Smear]',
    'FB0038': 'Breast,Left (US guided PCNA)(Des)[Smear with cell block]',
    'FB0039': 'Breast,Left (US guided PCNA)(Des)[Smear]',
    'FB0042': 'Breast,Right (US guided PCNA)(Des)[Smear with cell block]',
    'FB0043': 'Breast,Right (US guided PCNA)(Des)[Smear]',
    'FB0045': 'Bronchial brushing (Des)[Liquid based cytology]',
    'FB0047': 'Bronchial washing (Des)[Liquid based cytology]',
    'FB0049': 'Catheter urine (Des)[Liquid based cytology]',
    'FB0050': 'Cervical scrape (Des)[Liquid based cytology]',
    'FB0055': 'Cerebrospinal fluid (Des)[Liquid based cytology]',
    'FB0056': 'Endometrial (Des)[Liquid based cytology]',
    'FB0058': 'Esophagus (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0059': 'Esophagus (EUS guided FNA)(Des)[Smear]',
    'FB0060': 'Gallbladder (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0061': 'Gallbladder (EUS guided FNA)(Des)[Smear]',
    'FB0064': 'Large intestine (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0065': 'Large intestine (EUS guided FNA)(Des)[Smear]',
    'FB0066': 'Liver (Fluoroscopy guided PCNA)(Des)[Smear with cell block]',
    'FB0067': 'Liver (US guided PCNA)(Des)[Smear with cell block]',
    'FB0068': 'Liver (Fluoroscopy guided PCNA)(Des)[Smear]',
    'FB0069': 'Liver (US guided PCNA)(Des)[Smear]',
    'FB0070': 'Lung,Left (CT guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0071': 'Lung,Left (EBUS guided TBNA)(Des)[Liquid based cytology with cell block]',
    'FB0072': 'Lung,Left (Fluoroscopy guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0073': 'Lung,Left (CT guided PCNA)(Des)[Liquid based cytology]',
    'FB0074': 'Lung,Left (EBUS guided TBNA)(Des)[Liquid based cytology]',
    'FB0075': 'Lung,Left (Fluoroscopy guided PCNA)(Des)[Liquid based cytology]',
    'FB0076': 'Lung,Left (CT guided PCNA)(Des)[Smear with cell block]',
    'FB0078': 'Lung,Left (Fluoroscopy guided PCNA)(Des)[Smear with cell block]',
    'FB0079': 'Lung,Left (CT guided PCNA)(Des)[Smear]',
    'FB0081': 'Lung,Left (Fluoroscopy guided PCNA)(Des)[Smear]',
    'FB0082': 'Lung,Right (CT guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0083': 'Lung,Right (EBUS guided TBNA)(Des)[Liquid based cytology with cell block]',
    'FB0084': 'Lung,Right (Fluoroscopy guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0085': 'Lung,Right (CT guided PCNA)(Des)[Liquid based cytology]',
    'FB0086': 'Lung,Right (EBUS guided TBNA)(Des)[Liquid based cytology]',
    'FB0087': 'Lung,Right (Fluoroscopy guided PCNA)(Des)[Liquid based cytology]',
    'FB0088': 'Lung,Right (CT guided PCNA)(Des)[Smear with cell block]',
    'FB0089': 'Lung,Right (EBUS guided TBNA)(Des)[Smear with cell block]',
    'FB0090': 'Lung,Right (Fluoroscopy guided PCNA)(Des)[Smear with cell block]',
    'FB0091': 'Lung,Right (CT guided PCNA)(Des)[Smear]',
    'FB0092': 'Lung,Right (EBUS guided TBNA)(Des)[Smear]',
    'FB0093': 'Lung,Right (Fluoroscopy guided PCNA)(Des)[Smear]',
    'FB0100': 'Mediastinum (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0101': 'Mediastinum (EBUS guided TBNA)(Des)[Smear]',
    'FB0102': 'Mediastinum (EUS guided FNA)(Des)[Smear]',
    'FB0103': 'Mediastinum (EBUS guided TBNA)(Des)[Smear with cell block]',
    'FB0106': 'Pancreas (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0107': 'Pancreas (EUS guided FNA)(Des)[Smear]',
    'FB0112': 'Parathyroid (US guided PCNA)(Des)[Smear with cell block]',
    'FB0113': 'Parathyroid (US guided PCNA)(Des)[Smear]',
    'FB0117': 'Pericardial fluid (Des)[Liquid based cytology]',
    'FB0120': 'Peritoneal washing (Des)[Liquid based cytology]',
    'FB0122': 'Peritoneum (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0123': 'Peritoneum (EUS guided FNA)(Des)[Smear]',
    'FB0125': 'Pleural fluid (Des)[Liquid based cytology]',
    'FB0127': 'Salivary gland,Left (US guided PCNA)(Des)[Smear with cell block]',
    'FB0128': 'Salivary gland,Left (US guided PCNA)(Des)[Smear]',
    'FB0129': 'Salivary gland,Right (US guided PCNA)(Des)[Smear with cell block]',
    'FB0130': 'Salivary gland,Right (US guided PCNA)(Des)[Smear]',
    'FB0131': 'Soft tissue (CT guided PCNA)(Des)[Smear with cell block]',
    'FB0132': 'Soft tissue (EBUS guided TBNA)(Des)[Smear with cell block]',
    'FB0133': 'Soft tissue (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0134': 'Soft tissue (US guided PCNA)(Des)[Smear with cell block]',
    'FB0135': 'Soft tissue (CT guided PCNA)(Des)[Smear]',
    'FB0136': 'Soft tissue (EBUS guided TBNA)(Des)[Smear]',
    'FB0137': 'Soft tissue (EUS guided FNA)(Des)[Smear]',
    'FB0138': 'Soft tissue (US guided PCNA)(Des)[Smear]',
    'FB0139': 'Spleen (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0140': 'Spleen (EUS guided FNA)(Des)[Smear]',
    'FB0142': 'Sputum (Des)[Liquid based cytology]',
    'FB0143': 'Stomach (EUS guided FNA)(Des)[Smear with cell block]',
    'FB0144': 'Stomach (EUS guided FNA)(Des)[Smear]',
    'FB0145': 'TBNA washing (Des)[Liquid based cytology]',
    'FB0159': 'Urethra & Pelvic washing (Des)[Liquid based cytology]',
    'FB0161': 'Vaginal scrape (Des)[Liquid based cytology]',
    'FB0164': 'Voided urine (Des)[Liquid based cytology]',
    'FB0166': 'Washed urine (Des)[Liquid based cytology]',
    'FB0167': 'Breast,Right (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0168': 'Breast,Left (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0169': 'Pancreas (EUS guided FNA)(Des)[Liquid based cytology]',
    'FB0174': 'Ascitic fluid (Des)[Liquid based cytology with cell block]',
    'FB0175': 'Pleural fluid (Des)[Liquid based cytology with cell block]',
    'FB0176': 'Specimen labeled (Des)[Liquid based cytology with cell block]',
    'FB0177': 'Specimen labeled (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0178': 'Parathyroid (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0180': 'Specimen labeled (EBUS guided TBNA)[Liquid based cytology]',
    'FB0181': 'Specimen labeled (EBUS guided TBNA)[Liquid based cytology with cell block]',
    'FB0182': 'Specimen labeled (CT guided PCNA)(Des)[Liquid based cytology]',
    'FB0183': 'Specimen labeled (CT guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0184': 'Specimen labeled (Fluoroscopy guided PCNA)(Des)[Liquid based cytology]',
    'FB0185': 'Specimen labeled (Fluoroscopy guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0186': 'Parathyroid (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0187': 'Lymph node (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0188': 'Lymph node (EUS guided FNA)(Des)[Liquid based cytology]',
    'FB0189': 'Lymph node (EBUS guided TBNA)(Des)[Liquid based cytology]',
    'FB0190': 'Thyroid (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0191': 'Thyroid (US guided PCNA)(Des)[Liquid based cytology]',
    'FB0192': 'Thyroid (US guided PCNA)(Des)[Smear with cell block]',
    'FB0193': 'Thyroid (US guided PCNA)(Des)[Smear]',
    'FB0195': 'Bladder irrigation (Des)[Liquid based cytology]',
    'FB0196': 'Breast,Left (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0197': 'Breast,Right (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0198': 'Lymph node (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0199': 'Lymph node (EUS guided FNA)(Des)[Liquid based cytology with cell block]',
    'FB0200': 'Lymph node (EBUS guided TBNA)(Des)[Liquid based cytology with cell block]',
    'FB0201': 'Pancreas (EUS guided FNA)(Des)[Liquid based cytology with cell block]',
    'FB0202': 'Specimen labeled (US guided PCNA)(Des)[Liquid based cytology with cell block]',
    'FB0203': 'Specimen labeled (EUS guided FNA)(Des)[Liquid based cytology with cell block]',
    'FB0204': 'Specimen labeled (EUS guided FNA)(Des)[Liquid based cytology]',
    'FB0205': 'Eye (Aspiration)(Des)[Liquid based cytology]',
    'FB0206': 'Eye (Aspiration)(Des)[Liquid based cytology with cell block]',
    'FB0207': 'Ampulla of vater (Des)[Liquid based cytology]',
    'FB0208': 'Ampulla of vater (Des)[Liquid based cytology with cell block]',
    'FB0209': 'Bile (Des)[Liquid based cytology with cell block]',
    'FB0210': 'Bile duct (Des)[Liquid based cytology]',
    'FB0211': 'Bile duct (Des)[Liquid based cytology with cell block]',
    'FB0212': 'Intraoperative washing fluid (Des)[Liquid based cytology]',
    'FB0213': 'Intraoperative washing fluid (Des)[Liquid based cytology with cell block]',
    'FB0214': 'Pancreas (Des)[Liquid based cytology]',
    'FB0215': 'Pancreas (Des)[Liquid based cytology with cell block]',
    'FB0216': 'Peritoneal washing (Des)[Liquid based cytology with cell block]',
    'FB0217': 'Pericardial fluid (Des)[Liquid based cytology with cell block]',
}

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col(ref):
    return "".join(ch for ch in ref if ch.isalpha())


def read_xlsx(path):
    """엑셀 첫 시트의 A열(코드)·B열(이름)을 {코드: 이름} 으로 읽는다 (openpyxl 없이 표준 라이브러리만)."""
    out = {}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(_NS + "t")))
        sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        if not sheets:
            return out
        root = ET.fromstring(z.read(sheets[0]))
        for row in root.iter(_NS + "row"):
            vals = {}
            for c in row.iter(_NS + "c"):
                t = c.get("t")
                if t == "inlineStr":
                    v = "".join(x.text or "" for x in c.iter(_NS + "t"))
                else:
                    ve = c.find(_NS + "v")
                    v = ve.text if ve is not None else ""
                    if t == "s" and v:
                        v = shared[int(v)]
                vals[_col(c.get("r", ""))] = (v or "").strip()
            code, name = vals.get("A", "").upper(), vals.get("B", "")
            if _CODE_RE.match(code) and name and code not in out:
                out[code] = name
    return out


class ExamTable:
    def __init__(self):
        self.codes = dict(BUILTIN)
        self.source = "내장 검사코드표"

    def load(self, path):
        """엑셀 파일이 있으면 내장 표에 덮어쓴다. 읽은 건수 반환 (실패/없음 0)."""
        if not path or not os.path.isfile(path):
            return 0
        try:
            data = read_xlsx(path)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile, ET.ParseError):
            return 0
        if data:
            self.codes = dict(BUILTIN)
            self.codes.update(data)
            self.source = os.path.basename(path)
        return len(data)

    def name(self, code):
        return self.codes.get((code or "").upper(), "")


def parse_categories(text):
    """'urine=urine,bladder|gyn=cervical' → {'urine': ['urine', 'bladder'], 'gyn': ['cervical']}"""
    out = {}
    for part in str(text or "").split("|"):
        if "=" in part:
            cat, words = part.split("=", 1)
            words = [w.strip().lower() for w in words.split(",") if w.strip()]
            if cat.strip() and words:
                out[cat.strip().lower()] = words
    return out


def parse_check_categories(text):
    """'Urine <30ml=urine|Vaginal=gyn' → {'Urine <30ml': 'urine', 'Vaginal': 'gyn'}"""
    out = {}
    for part in str(text or "").split("|"):
        if "=" in part:
            hdr, cat = part.split("=", 1)
            if hdr.strip() and cat.strip():
                out[hdr.strip()] = cat.strip().lower()
    return out


def categories_of(exam_name, cfg):
    """검사명에 해당하는 검체 분류 집합 (예: {'urine', 'inst'})."""
    name = " ".join((exam_name or "").lower().split())
    return {cat for cat, words in parse_categories(cfg.get("exam_categories")).items()
            if any(w in name for w in words)}


def check_enabled(item, header, cfg):
    """목록 체크 칸(header)을 이 항목에서 쓸 수 있는지.
    검사코드가 없거나 표에 없는 코드(검사명 모름)면 예전처럼 모두 사용 가능."""
    if not cfg.get("limit_checks_by_exam", True) or not getattr(item, "exam_name", ""):
        return True
    cat = parse_check_categories(cfg.get("check_categories")).get(header)
    if not cat:
        return True
    return cat in categories_of(item.exam_name, cfg)


def effective_checks(item, cfg):
    """저장 시 실제로 적용할 체크 (비활성 칸은 체크돼 있어도 무시)."""
    return {k: v for k, v in item.checks.items() if v and check_enabled(item, k, cfg)}
