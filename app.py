import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# -------------------------------------------------------------
# 0. 설정 및 구글 시트 Webhook URL
# -------------------------------------------------------------

GAS_WEBHOOK_URL = st.secrets["GAS_WEBHOOK_URL"]
st.set_page_config(
    page_title="블라인드C 블스터디 조 선정",
    page_icon="👥",
    layout="wide"
)

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = {}
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# -------------------------------------------------------------
# 1. API 통신 헬퍼 함수
# -------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_data():
    """구글 시트에서 전체 데이터 가져오기"""
    try:
        res = requests.get(GAS_WEBHOOK_URL, allow_redirects=True, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"데이터 연동 중 오류 발생: {e}")
    return {"submissions": [], "requests": [], "configs": []}

def post_action(payload):
    """구글 시트로 액션 전송하기"""
    try:
        res = requests.post(GAS_WEBHOOK_URL, json=payload, allow_redirects=True, timeout=10)
        return res.status_code == 200
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")
        return False

# -------------------------------------------------------------
# 2. 시작 화면 (로그인 / 본인 확인)
# -------------------------------------------------------------
if not st.session_state.logged_in:
    # 중앙 정렬을 위한 스타일
    st.markdown("""
        <style>
        .main-title {
            text-align: center;
            font-size: 2.3rem;
            font-weight: 800;
            margin-top: 50px;
            margin-bottom: 30px;
            color: #1E293B;
        }
        </style>
        <div class="main-title">블라인드C 블스터디 조 선정</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            name = st.text_input("이름", placeholder="이름을 입력하세요")
            major = st.text_input("전공", placeholder="아융 혹은 전자로 입력하세요")
            grade = st.text_input("학년", placeholder="숫자만 입력하세요")
            student_id = st.text_input("학번", placeholder="예: 20260000(8자리)")
            
            submit_button = st.form_submit_button("입력완료", use_container_width=True)

            if submit_button:
                # 공백 제거
                name_clean = name.strip()
                major_clean = major.strip()
                grade_clean = grade.strip()
                id_clean = student_id.strip()

                if not name_clean or not major_clear or not grade_clean or not id_clean:
                    st.warning("이름, 전공, 학년, 학번을 모두 입력해주세요.")
                else:
                    # 관리자 조건 확인: 이름="나는야임원진", 전공="공통", 학년="n", 학번="00000000"
                    if name_clean == "나는야임원진" and major_clean =="공통" and grade_clean == "n" and id_clean == "00000000":
                        st.session_state.is_admin = True
                    else:
                        st.session_state.is_admin = False

                    st.session_state.logged_in = True
                    st.session_state.user_info = {
                        "name": name_clean,
                        "major": major_clean,
                        "grade": grade_clean,
                        "student_id": id_clean
                    }
                    st.rerun()

# -------------------------------------------------------------
# 3-1. 관리자 화면 (임원진 대시보드)
# -------------------------------------------------------------
elif st.session_state.is_admin:
    # 상단 헤더
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title("🛡️ 관리자 대시보드 (임원진 전용)")
    with header_col2:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.is_admin = False
            st.rerun()

    data = fetch_data()
    submissions = pd.DataFrame(data.get("submissions", []))
    requests_list = data.get("requests", [])

    # 2열 분할 레이아웃 (좌측: 요청 메시지함, 우측: 시간대 현황 & 설정)
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("📬 시간 추가 요청 목록")
        if requests_list:
            for req in reversed(requests_list):
                with st.expander(f"📌 {req.get('이름', '익명')} ({req.get('학번', '-')})", expanded=True):
                    st.write(f"**요청 내용:** {req.get('요청내용', '')}")
                    st.caption(f"접수: {req.get('요청일시', '')}")
        else:
            st.info("도착한 시간 추가 요청이 없습니다.")

    with col_right:
        tab1, tab2, tab3 = st.tabs(["📊 신청 현황 요약", "📋 전체 제출 명단", "⚙️ 시간대 추가"])
        
        with tab1:
            st.subheader("시간대별 신청 인원")
            if not submissions.empty and "선택시간" in submissions.columns:
                # 시간대별 집계
                count_df = submissions["선택시간"].value_counts().reset_index()
                count_df.columns = ["시간대", "신청자 수"]
                st.dataframe(count_df, use_container_width=True)

                # 특정 시간대 선택 시 명단 필터
                selected_filter = st.selectbox("특정 시간대 신청자 보기", ["전체"] + list(count_df["시간대"]))
                if selected_filter != "전체":
                    filtered_df = submissions[submissions["선택시간"] == selected_filter]
                    st.write(f"**[{selected_filter}] 신청자 ({len(filtered_df)}명)**")
                    st.dataframe(filtered_df[["이름", "전공", "학년", "학번", "제출일시"]], use_container_width=True)
            else:
                st.info("아직 제출된 신청 내역이 없습니다.")

        with tab2:
            st.subheader("전체 지원자 원본 데이터")
            if not submissions.empty:
                st.dataframe(submissions, use_container_width=True)
                csv = submissions.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 CSV 파일로 다운로드",
                    data=csv,
                    file_name=f"study_matching_{datetime.now().strftime('%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("데이터가 없습니다.")

        with tab3:
            st.subheader("새로운 시간대 슬롯 추가")
            with st.form("add_slot_form"):
                add_day = st.selectbox("요일", ["월", "화", "수", "목", "금", "토", "일"])
                add_time = st.text_input("시간대", placeholder="예: 20:00~21:00")
                add_submit = st.form_submit_button("시간대 추가")

                if add_submit:
                    if add_time.strip():
                        success = post_action({
                            "action": "add_config_slot",
                            "day": add_day,
                            "time_slot": add_time.strip()
                        })
                        if success:
                            st.success(f"{add_day}요일 {add_time} 시간대가 추가되었습니다!")
                            st.rerun()
                    else:
                        st.warning("시간대를 입력해주세요.")

# -------------------------------------------------------------
# 3-2. 일반 사용자 화면 (시간표 표 형태 Grid UI)
# -------------------------------------------------------------
else:
    user = st.session_state.user_info

    # 1. 상단 프로필 바 & 다시 입력 버튼
    head_col1, head_col2 = st.columns([8, 2])
    with head_col1:
        st.subheader(f"👋 {user['name']}님 ({user['grade']}학년 / {user['student_id']})")
        st.caption("아래 시간표에서 참여 가능한 시간대를 **1개만** 클릭한 후 제출해 주세요.")
    with head_col2:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.selected_slot = None
            st.rerun()

    st.markdown("---")

    # 선택된 슬롯 세션 상태 초기화
    if "selected_slot" not in st.session_state:
        st.session_state.selected_slot = None

    # 기본 시간표 매트릭스 정의
    days = ["월", "화", "수", "목", "금"]
    time_slots = [
        "15:00~16:00",
        "16:00~17:00",
        "17:00~18:00",
        "18:00~19:00",
        "19:00~20:00"
    ]

    # 관리자 추가 시간대 로드
    data = fetch_data()
    configs = data.get("configs", [])

    # 표 형태 스타일 커스텀 CSS (격자 가독성 향상)
    st.markdown("""
        <style>
        .table-header {
            text-align: center;
            font-weight: 700;
            background-color: #F1F5F9;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            color: #1E293B;
        }
        .time-label {
            text-align: center;
            font-size: 0.85rem;
            font-weight: 600;
            color: #64748B;
            padding: 12px 0;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📅 희망 스터디 시간표")

    # 시간표 그리드 헤더 (시간 열 + 요일 5열)
    header_cols = st.columns([1.2, 1, 1, 1, 1, 1])
    header_cols[0].markdown("<div class='table-header'>시간대</div>", unsafe_allow_html=True)
    for i, day in enumerate(days):
        header_cols[i + 1].markdown(f"<div class='table-header'>{day}요일</div>", unsafe_allow_html=True)

    # 기본 15:00 ~ 20:00 격자 생성
    for slot in time_slots:
        row_cols = st.columns([1.2, 1, 1, 1, 1, 1])
        row_cols[0].markdown(f"<div class='time-label'>{slot}</div>", unsafe_allow_html=True)

        for i, day in enumerate(days):
            current_choice = f"{day}요일 {slot}"
            is_selected = (st.session_state.selected_slot == current_choice)
            
            # 선택된 버튼은 primary(색상 강조) 스타일 적용
            btn_type = "primary" if is_selected else "secondary"
            btn_label = f"선택됨" if is_selected else "선택"

            if row_cols[i + 1].button(btn_label, key=f"btn_{day}_{slot}", type=btn_type, use_container_width=True):
                st.session_state.selected_slot = current_choice
                st.rerun()

    # 관리자가 추가 등록한 특별 시간대가 있다면 별도 표기
    if configs:
        st.markdown("<br>##### ➕ 추가 개설된 특별 시간대", unsafe_allow_html=True)
        cfg_cols = st.columns(min(len(configs), 4))
        for idx, cfg in enumerate(configs):
            slot_name = f"{cfg.get('요일')}요일 {cfg.get('시간대')}"
            is_selected = (st.session_state.selected_slot == slot_name)
            btn_type = "primary" if is_selected else "secondary"
            btn_label = f"선택됨 ({slot_name})" if is_selected else slot_name
            
            with cfg_cols[idx % 4]:
                if st.button(btn_label, key=f"btn_cfg_{idx}", type=btn_type, use_container_width=True):
                    st.session_state.selected_slot = slot_name
                    st.rerun()

    st.markdown("---")

    # 하단 상태 표시 및 최종 제출 버튼 영역
    sub_col1, sub_col2 = st.columns([3, 2])
    with sub_col1:
        if st.session_state.selected_slot:
            st.info(f"선택한 시간대: **{st.session_state.selected_slot}**")
        else:
            st.warning("위 시간표에서 원하는 시간대를 하나 선택해 주세요.")

    with sub_col2:
        if st.button("선택완료 및 제출", type="primary", use_container_width=True):
            if not st.session_state.selected_slot:
                st.error("시간대를 먼저 선택해 주세요!")
            else:
                with st.spinner("구글 시트에 저장 중..."):
                    payload = {
                        "action": "submit_slot",
                        "name": user["name"],
                        "grade": user["grade"],
                        "student_id": user["student_id"],
                        "selected_slot": st.session_state.selected_slot
                    }
                    if post_action(payload):
                        st.cache_data.clear()
                        st.success(f"🎉 '{st.session_state.selected_slot}' 시간대로 제출되었습니다!")
                    else:
                        st.error("제출에 실패했습니다. 다시 시도해 주세요.")

    # 3-2-1. 시간 추가 요청 영역
    st.markdown("<br>", unsafe_allow_html=True)
    req_col1, req_col2, _ = st.columns([1.8, 1.5, 3])
    with req_col1:
        st.markdown("<p style='font-size: 0.85rem; color: gray; margin-top: 8px;'>원하는 시간대가 없다면?</p>", unsafe_allow_html=True)
    with req_col2:
        if st.button("시간 추가 요청", key="btn_req_time", use_container_width=True):
            st.session_state.show_request_form = not st.session_state.get("show_request_form", False)

    if st.session_state.get("show_request_form", False):
        with st.container():
            st.info("💡 관리자에게 개설 희망 시간대나 전달 사항을 남겨주세요.")
            with st.form("message_form"):
                req_msg = st.text_area("요청 메시지", placeholder="예: 금요일 13시~15시 희망합니다!")
                send_msg = st.form_submit_button("메시지 전송")

                if send_msg:
                    if req_msg.strip():
                        success = post_action({
                            "action": "request_time",
                            "name": user["name"],
                            "student_id": user["student_id"],
                            "message": req_msg.strip()
                        })
                        if success:
                            st.cache_data.clear()
                            st.success("관리자에게 메시지가 전송되었습니다!")
                            st.session_state.show_request_form = False
                    else:
                        st.warning("메시지 내용을 입력해주세요.")
