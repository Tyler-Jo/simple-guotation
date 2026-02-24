import io
import os
from datetime import datetime
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from PIL import Image
from reportlab.lib.utils import ImageReader

# [1] 한글 폰트 설정
FONT_PATH = "NanumGothic.ttf" 
FONT_NAME = "NanumGothic"
try:
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
except:
    st.error("폰트를 로드할 수 없습니다. 경로를 확인하세요.")

def number_to_korean(num):
    units = ['', '만', '억', '조']
    digits = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
    positions = ['', '십', '백', '천']
    if num == 0: return "영"
    result, chunk_count = [], 0
    while num > 0:
        chunk = num % 10000
        if chunk > 0:
            chunk_str = ""
            for i, d in enumerate(str(chunk)[::-1]):
                digit = int(d)
                if digit > 0: chunk_str = digits[digit] + positions[i] + chunk_str
            result.append(chunk_str + units[chunk_count])
        num //= 10000
        chunk_count += 1
    return "".join(result[::-1])

# [2] PDF 생성 함수 (공급자 정보 매개변수 추가)
def generate_pdf(data_list, client_info, supplier_info, stamp_file=None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    table_width = 500
    start_x = 50
    end_x = start_x + table_width 

    # 1. 제목
    c.setLineWidth(1)
    c.rect(width/2 - 80, height - 70, 160, 40)
    c.setFont(FONT_NAME, 24)
    c.drawCentredString(width/2, height - 60, "견 적 서")

    # 2. 공급자 정보표 (사용자 입력값 반영)
    s_col_widths = [25, 55, 110, 40, 70]
    s_table_width = sum(s_col_widths)
    supplier_data = [
        ['공\n급\n자', '등록\n번호', supplier_info['biz_num'], '', ''],
        ['', '상 호', supplier_info['company'], '성 명', supplier_info['name']],
        ['', '소재지', supplier_info['address'], '', ''],
        ['', '업 태', supplier_info['biz_type'], '종 목', supplier_info['biz_item']],
        ['', '전화.fax', supplier_info['contact'], '', '']
    ]
    s_table = Table(supplier_data, colWidths=s_col_widths, rowHeights=[24]*5)
    s_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (0,0), (0,4)),
        ('SPAN', (2,0), (4,0)),
        ('SPAN', (2,2), (4,2)),
        ('SPAN', (2,4), (4,4)),
    ]))
    s_table.wrapOn(c, width, height)
    s_table.drawOn(c, end_x - s_table_width, height - 210)

    # 3. 도장 이미지
    if stamp_file:
            try:
                img = Image.open(stamp_file)
                c.drawImage(ImageReader(img), 532, height - 137, width=22, height=22, mask='auto')
            except:
                pass

    # 4. 수신자 정보
    c.setFont(FONT_NAME, 12)
    c.drawString(start_x + 10, height - 120, f"{client_info['date']}")
    c.setFont(FONT_NAME, 16)
    c.drawString(start_x + 10, height - 150, f"{client_info['name']} 귀하")
    c.setFont(FONT_NAME, 11)
    c.drawString(start_x + 10, height - 185, "아래와 같이 견적합니다.")

    # 5. 합계 금액
    total_amount = sum(item['amount'] for item in data_list)
    c.setLineWidth(1.2)
    c.rect(start_x, height - 255, table_width, 30)
    c.setFont(FONT_NAME, 11)
    c.drawString(start_x + 10, height - 243, "합계금액 (공급가액)")
    amount_korean = f"₩ 금 {number_to_korean(total_amount)} 원정 (₩{total_amount:,}원)"
    c.drawRightString(end_x - 10, height - 243, amount_korean)

    # 6. 품목 상세 테이블
    header = ['품 명', '수 량', '단 위', '단 가(원)', '금 액(원)', '비 고']
    main_data = [header]
    for item in data_list:
        main_data.append([item['name'], item['qty'], item['unit'], f"{item['price']:,}", f"{item['amount']:,}", ""])
    for _ in range(12 - len(data_list)):
        main_data.append(['', '', '', '', '', ''])
    main_data.append([f"※ 비고사항: {client_info['note']}", '', '', '', '', ''])

    m_table = Table(main_data, colWidths=[160, 40, 40, 90, 90, 80], rowHeights=22)
    m_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('SPAN', (0, 13), (5, 13)),
    ]))
    m_table.wrapOn(c, width, height)
    m_table.drawOn(c, start_x, height - 560)

    # 7. 하단 정보 (사용자 입력 계좌 반영)
    c.setFillColor(colors.lightgrey)
    c.rect(start_x, 70, table_width, 25, fill=1)
    c.setFillColor(colors.black)
    c.drawString(start_x + 10, 78, f"계좌번호 : {supplier_info['bank_account']}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- [3] Streamlit UI ---
st.set_page_config(page_title="견적서 생성기", layout="wide")
st.title("📋 견적서 생성")

if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None

with st.sidebar:
    with st.popover("사용 방법 안내", icon="❓"):
        st.markdown("""
        ### 📑 견적서 작성 가이드
        1. **공급자 정보**: 상단 메뉴에서 공급자 정보를 확인 및 수정하세요.
        2. **설정**: 작성할 **품목 수**를 조절하세요.
        3. **도장**: 인감 도장 파일을 업로드하세요.
        4. **데이터 확정**: 하단 버튼을 눌러 생성 후 PDF를 다운로드하세요.
        """)
    
    st.header("⚙️ 기본 설정")
    num_items = st.number_input("품목 수", 1, 12, 5)
    user_stamp = st.file_uploader("도장 첨부 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])

# [4] 공급자 정보 입력 섹션 (기존 값들을 기본값으로 설정)
with st.expander("🏢 공급자 정보 수정", expanded=False):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_company = st.text_input("상호", value="구룡석공예")
        s_name = st.text_input("성명", value="황의왕")
        s_biz_num = st.text_input("등록번호", value="3130662919")
        s_bank = st.text_input("계좌번호", value="농협 황의왕 467087-56-040781")
    with col_s2:
        s_address = st.text_input("소재지", value="충남 보령시 웅천읍 무창포로 226")
        s_biz_type = st.text_input("업태", value="제조")
        s_biz_item = st.text_input("종목", value="석재")
        s_contact = st.text_input("전화.fax", value="010-7753-6605/041-932-6605")

# [5] 메인 입력 폼
with st.form("invoice_form"):
    st.subheader("👤 수신자 정보")
    col1, col2 = st.columns(2)
    c_name = col1.text_input("수신자 명", "낙원공원묘지")
    c_date = col2.date_input("발행 일자", datetime.now())
    c_note = st.text_area("비고 사항", "계약금 10% 입금 시 진행하겠습니다.")
    
    st.divider()
    st.subheader("📦 품목 상세")
    items = []
    for i in range(num_items):
        cols = st.columns([3, 1, 1, 2])
        name = cols[0].text_input(f"품명 {i+1}", key=f"n{i}")
        qty = cols[1].number_input(f"수량", key=f"q{i}", min_value=1, step=1)
        unit = cols[2].text_input(f"단위", "세트", key=f"u{i}")
        price = cols[3].number_input(f"단가", key=f"p{i}", min_value=0, step=1000)
        items.append({'name': name, 'qty': qty, 'unit': unit, 'price': price, 'amount': qty * price})
    
    submit_btn = st.form_submit_button("🚀 견적서 생성 (데이터 확정)")

# [6] PDF 처리 및 다운로드
if submit_btn:
    client_payload = {
        "name": c_name,
        "date": c_date.strftime("%Y년 %m월 %d일"),
        "note": c_note
    }
    # 입력받은 공급자 정보 묶기
    supplier_payload = {
        "company": s_company,
        "name": s_name,
        "biz_num": s_biz_num,
        "address": s_address,
        "biz_type": s_biz_type,
        "biz_item": s_biz_item,
        "contact": s_contact,
        "bank_account": s_bank
    }
    
    st.session_state.pdf_data = generate_pdf(items, client_payload, supplier_payload, user_stamp)
    st.session_state.client_name = c_name

if st.session_state.pdf_data is not None:
    st.success(f"{st.session_state.client_name} 귀하의 견적서가 준비되었습니다.")
    st.download_button(
        label="📥 완성된 PDF 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"견적서_{st.session_state.client_name}.pdf",
        mime="application/pdf"
    )