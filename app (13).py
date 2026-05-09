import streamlit as st
from supabase import create_client
import hashlib
import uuid
import random
from datetime import datetime

# ─────────────────────────────────────────────
# 🔌 Supabase 연결
# ─────────────────────────────────────────────
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ─────────────────────────────────────────────
# 세션 초기화
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ─────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────
def hex_encode(text):
    """문자열 → SHA256 16진수"""
    return hashlib.sha256(text.encode()).hexdigest()

def generate_blogger_code():
    """고유 블로거 코드 생성 (12자리 16진수)"""
    return uuid.uuid4().hex[:12].upper()

def random_color_hex():
    """랜덤 단색 16진수 색상"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
        "#BB8FCE", "#85C1E9", "#82E0AA", "#F0B27A"
    ]
    return random.choice(colors)


# ─────────────────────────────────────────────
# 🔐 로그인 화면
# ─────────────────────────────────────────────
def login_page():
    st.title("🔐 로그인")
    st.markdown("---")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("로그인", use_container_width=True):
            if not username or not password:
                st.error("아이디와 비밀번호를 입력하세요.")
                return
            hex_pw = hex_encode(password)
            result = supabase.table("users")\
                .select("*")\
                .eq("username", username)\
                .eq("password", hex_pw)\
                .execute()
            if result.data:
                st.session_state.logged_in = True
                st.session_state.user = result.data[0]
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")

    with col2:
        if st.button("회원가입", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()


# ─────────────────────────────────────────────
# 📝 회원가입 화면
# ─────────────────────────────────────────────
def signup_page():
    st.title("📝 회원가입")
    st.markdown("---")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    password2 = st.text_input("비밀번호 확인", type="password")

    if st.button("가입하기", use_container_width=True):
        if not username or not password:
            st.error("아이디와 비밀번호를 입력하세요.")
            return
        if password != password2:
            st.error("비밀번호가 일치하지 않습니다.")
            return
        if len(password) < 4:
            st.error("비밀번호는 4자 이상이어야 합니다.")
            return

        # 중복 확인
        existing = supabase.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        if existing.data:
            st.error("이미 사용 중인 아이디입니다.")
            return

        # 블로거 코드 중복 없이 생성
        while True:
            code = generate_blogger_code()
            check = supabase.table("users")\
                .select("id")\
                .eq("blogger_code", code)\
                .execute()
            if not check.data:
                break

        hex_pw = hex_encode(password)

        supabase.table("users").insert({
            "username": username,
            "password": hex_pw,
            "blogger_code": code,
            "subscriptions": []
        }).execute()

        st.success(f"🎉 가입 완료!")
        st.info(f"나의 블로거 코드: **{code}**\n\n(다른 사람이 이 코드로 나를 구독할 수 있습니다.)")

    st.markdown("---")
    if st.button("← 로그인으로 돌아가기"):
        st.session_state.page = "login"
        st.rerun()


# ─────────────────────────────────────────────
# 📄 게시글 카드 표시
# ─────────────────────────────────────────────
def display_post(post):
    with st.container():
        # 썸네일
        thumbnail = post.get("thumbnail", "")
        if thumbnail and thumbnail.startswith("#"):
            st.markdown(
                f'<div style="background:{thumbnail};height:120px;'
                f'border-radius:10px;margin-bottom:8px;"></div>',
                unsafe_allow_html=True
            )
        elif thumbnail:
            st.image(thumbnail, use_container_width=True)

        # 제목 / 부제
        st.subheader(post.get("title", "(제목 없음)"))
        if post.get("subtitle"):
            st.caption(post["subtitle"])

        # 본문
        st.write(post.get("text", ""))

        # 첨부 이미지
        if post.get("image"):
            st.image(post["image"], use_container_width=True)

        # 메타 정보
        time_str = post.get("time", "")[:16] if post.get("time") else ""
        st.caption(f"🕒 {time_str}  |  ✍️ 블로거 코드: `{post.get('code', '')}`")

        # 추천 / 구독 버튼
        col1, col2 = st.columns(2)
        with col1:
            likes = post.get("likes", 0)
            if st.button(f"👍 추천 {likes}", key=f"like_{post['id']}"):
                supabase.table("posts")\
                    .update({"likes": likes + 1})\
                    .eq("id", post["id"])\
                    .execute()
                st.rerun()
        with col2:
            blogger_code = post.get("code", "")
            my_code = st.session_state.user.get("blogger_code", "")
            subs = st.session_state.user.get("subscriptions") or []
            if blogger_code != my_code:
                if blogger_code not in subs:
                    if st.button("➕ 구독", key=f"sub_{post['id']}"):
                        subs.append(blogger_code)
                        supabase.table("users")\
                            .update({"subscriptions": subs})\
                            .eq("id", st.session_state.user["id"])\
                            .execute()
                        st.session_state.user["subscriptions"] = subs
                        st.success("구독 완료!")
                        st.rerun()
                else:
                    if st.button("✅ 구독 중", key=f"unsub_{post['id']}"):
                        subs.remove(blogger_code)
                        supabase.table("users")\
                            .update({"subscriptions": subs})\
                            .eq("id", st.session_state.user["id"])\
                            .execute()
                        st.session_state.user["subscriptions"] = subs
                        st.rerun()

        st.markdown("---")


# ─────────────────────────────────────────────
# ✍️ 글쓰기 화면
# ─────────────────────────────────────────────
def write_post_page():
    st.title("✍️ 글쓰기")
    st.markdown("---")

    title    = st.text_input("제목 *")
    subtitle = st.text_input("부제 (선택)")
    text     = st.text_area("본문 *", height=200)

    st.markdown("##### 파일 첨부 (선택)")
    uploaded_file = st.file_uploader(
        "이미지 또는 파일", type=["png", "jpg", "jpeg"]
    )

    st.markdown("##### 썸네일 지정 (선택 — 미지정 시 랜덤 단색)")
    use_thumb = st.checkbox("썸네일 직접 업로드")
    thumb_file = None
    if use_thumb:
        thumb_file = st.file_uploader(
            "썸네일 이미지", type=["png", "jpg", "jpeg"], key="thumb"
        )

    st.markdown("---")
    if st.button("📤 올리기", use_container_width=True):
        if not title:
            st.error("제목은 필수입니다.")
            return
        if not text:
            st.error("본문은 필수입니다.")
            return

        image_url = None
        thumbnail_val = random_color_hex()

        # 첨부 파일 업로드
        if uploaded_file:
            fname = f"{uuid.uuid4().hex}_{uploaded_file.name}"
            supabase.storage.from_("images").upload(
                fname, uploaded_file.read(),
                {"content-type": uploaded_file.type}
            )
            image_url = supabase.storage.from_("images").get_public_url(fname)

        # 썸네일 업로드
        if thumb_file:
            tname = f"thumb_{uuid.uuid4().hex}_{thumb_file.name}"
            supabase.storage.from_("images").upload(
                tname, thumb_file.read(),
                {"content-type": thumb_file.type}
            )
            thumbnail_val = supabase.storage.from_("images").get_public_url(tname)

        # posts 테이블에 새 행 삽입
        supabase.table("posts").insert({
            "image"    : image_url,
            "time"     : datetime.now().isoformat(),
            "text"     : text,
            "code"     : st.session_state.user["blogger_code"],
            "title"    : title,
            "subtitle" : subtitle if subtitle else None,
            "thumbnail": thumbnail_val,
            "likes"    : 0
        }).execute()

        st.success("✅ 게시글이 등록되었습니다!")
        st.rerun()


# ─────────────────────────────────────────────
# 🔍 검색 화면
# ─────────────────────────────────────────────
def search_page():
    st.title("🔍 검색")
    query = st.text_input("제목, 본문, 또는 블로거 코드로 검색")

    if st.button("검색") and query:
        # 블로거 코드 정확히 일치 OR 제목/본문 포함
        by_code  = supabase.table("posts").select("*")\
            .eq("code", query.upper()).execute().data
        by_title = supabase.table("posts").select("*")\
            .ilike("title", f"%{query}%").execute().data
        by_text  = supabase.table("posts").select("*")\
            .ilike("text", f"%{query}%").execute().data

        seen = set()
        results = []
        for post in by_code + by_title + by_text:
            if post["id"] not in seen:
                seen.add(post["id"])
                results.append(post)

        if results:
            st.success(f"{len(results)}개의 게시글을 찾았습니다.")
            for post in results:
                display_post(post)
        else:
            st.info("검색 결과가 없습니다.")


# ─────────────────────────────────────────────
# ⭐ 추천 화면
# ─────────────────────────────────────────────
def recommended_page():
    st.title("⭐ 추천")
    results = supabase.table("posts").select("*")\
        .order("likes", desc=True).limit(30).execute().data
    if results:
        for post in results:
            display_post(post)
    else:
        st.info("게시글이 없습니다.")


# ─────────────────────────────────────────────
# 🔥 인기 화면
# ─────────────────────────────────────────────
def popular_page():
    st.title("🔥 인기 TOP 10")
    results = supabase.table("posts").select("*")\
        .order("likes", desc=True).limit(10).execute().data
    if results:
        for i, post in enumerate(results, 1):
            st.markdown(f"### #{i}")
            display_post(post)
    else:
        st.info("게시글이 없습니다.")


# ─────────────────────────────────────────────
# 📰 내가 구독한 블로거
# ─────────────────────────────────────────────
def subscribed_page():
    st.title("📰 내가 구독한 블로거")

    subs = st.session_state.user.get("subscriptions") or []

    # 구독 추가
    new_code = st.text_input("블로거 코드로 구독하기")
    if st.button("구독 추가"):
        new_code = new_code.upper()
        if not new_code:
            st.error("블로거 코드를 입력하세요.")
        elif new_code == st.session_state.user["blogger_code"]:
            st.error("자기 자신은 구독할 수 없습니다.")
        elif new_code in subs:
            st.warning("이미 구독 중인 블로거입니다.")
        else:
            # 존재하는 코드인지 확인
            check = supabase.table("users")\
                .select("id")\
                .eq("blogger_code", new_code)\
                .execute()
            if not check.data:
                st.error("존재하지 않는 블로거 코드입니다.")
            else:
                subs.append(new_code)
                supabase.table("users")\
                    .update({"subscriptions": subs})\
                    .eq("id", st.session_state.user["id"])\
                    .execute()
                st.session_state.user["subscriptions"] = subs
                st.success(f"`{new_code}` 구독 완료!")
                st.rerun()

    st.markdown("---")

    # 구독 목록 표시
    if subs:
        st.markdown(f"**구독 중인 블로거 {len(subs)}명**")
        for code in subs:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(code)
            with col2:
                if st.button("구독 취소", key=f"unsub_list_{code}"):
                    subs.remove(code)
                    supabase.table("users")\
                        .update({"subscriptions": subs})\
                        .eq("id", st.session_state.user["id"])\
                        .execute()
                    st.session_state.user["subscriptions"] = subs
                    st.rerun()

        st.markdown("---")
        st.subheader("구독한 블로거 최신 글")
        posts = supabase.table("posts").select("*")\
            .in_("code", subs)\
            .order("time", desc=True)\
            .execute().data
        if posts:
            for post in posts:
                display_post(post)
        else:
            st.info("구독한 블로거의 글이 없습니다.")
    else:
        st.info("아직 구독한 블로거가 없습니다.")


# ─────────────────────────────────────────────
# 🏠 홈 (사이드바 + 메뉴 라우팅)
# ─────────────────────────────────────────────
def home_page():
    user = st.session_state.user

    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.markdown(f"블로거 코드")
        st.code(user['blogger_code'])
        st.markdown("---")

        menu = st.radio(
            "메뉴",
            ["✍️ 글쓰기", "🔍 검색", "⭐ 추천", "🔥 인기", "📰 내가 구독한 블로거"]
        )

        st.markdown("---")
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    if menu == "✍️ 글쓰기":
        write_post_page()
    elif menu == "🔍 검색":
        search_page()
    elif menu == "⭐ 추천":
        recommended_page()
    elif menu == "🔥 인기":
        popular_page()
    elif menu == "📰 내가 구독한 블로거":
        subscribed_page()


# ─────────────────────────────────────────────
# 🚀 앱 진입점
# ─────────────────────────────────────────────
st.set_page_config(page_title="블로그 앱", page_icon="📝", layout="wide")

if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    home_page()
