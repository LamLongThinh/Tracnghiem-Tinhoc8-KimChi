import streamlit as st
from docx import Document
from datetime import datetime
import datetime as dt
import re, json, pandas as pd, os, random, time
from io import BytesIO
import base64

# ====== Cấu hình cơ bản (GIỮ NGUYÊN) ======
QUIZ_FILE = "questions.json"
SCORES_FILE = "scores.xlsx"
ADMIN_PASSWORD = "admin123"
EXPECTED_COLUMNS = ["Tên Học Sinh", "Lớp", "Điểm", "Tổng Số Câu", "Thời Gian Nộp Bài"]
DEFAULT_TIME_LIMIT = 45

st.markdown(
    """
    <h2 style='text-align: center; font-weight: 800;'>
        📝 TRẮC NGHIỆM – TIN HỌC 8
    </h2>
    <h4 style='text-align: center; color: gray; font-weight: 700;'>
        KIẾN THỨC TRỌNG TÂM GIỮA HỌC KÌ 1 NĂM HỌC 2025–2026
    </h4>
    """,
    unsafe_allow_html=True
)
# ====== Khởi tạo file bảng điểm (GIỮ NGUYÊN) ======
def init_scores_file():
    if not os.path.exists(SCORES_FILE):
        pd.DataFrame(columns=EXPECTED_COLUMNS).to_excel(SCORES_FILE, index=False)
init_scores_file()

# ====== Các hàm tiện ích (GIỮ NGUYÊN load_quiz, load_quiz_from_word, save_quiz, get_shuffled_quiz) ======
def load_quiz():
    if os.path.exists(QUIZ_FILE):
        with open(QUIZ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_quiz_from_word(file):
    doc = Document(file)
    text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
    blocks = re.split(r"(Câu\s*\d+[.:])", text)
    quiz, content_blocks = [], []
    for i in range(1, len(blocks), 2):
        if i + 1 < len(blocks):
            content_blocks.append(blocks[i] + blocks[i + 1])
    for block in content_blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines: continue
        q_text = re.sub(r"^Câu\s*\d+[.:]\s*", "", lines[0]).strip()
        options, correct = {}, None
        for line in lines[1:]:
            if re.match(r"^[A-D]\.", line): letter, content = line.split('.', 1); options[letter.strip()] = content.strip()
            elif re.search(r"đáp\s*án", line, flags=re.IGNORECASE):
                correct = line.split(":")[-1].strip().upper()
        if len(options) == 4 and correct in options:
            # Bổ sung trường 'image_base64' rỗng để lưu ảnh
            quiz.append({"question": q_text, "options": [options[k] for k in ["A","B","C","D"]], "answer": options[correct], "image_base64": None})
    return quiz

def save_quiz(quiz):
    with open(QUIZ_FILE, "w", encoding="utf-8") as f:
        json.dump(quiz, f, ensure_ascii=False, indent=4)
    st.success(f"✅ Đã lưu {len(quiz)} câu hỏi vào '{QUIZ_FILE}'.")

def get_shuffled_quiz(qz):
    qz = qz.copy()
    random.shuffle(qz)
    for q in qz:
        random.shuffle(q["options"])
    return qz

# =========================================================================
# Hàm student_ui() đã CẬP NHẬT để bắt học sinh nhấn nút Bắt đầu
# =========================================================================
def student_ui():
    st.header("📚 Khu vực Thi Trắc Nghiệm")
    quiz_raw = load_quiz()
    if not quiz_raw:
        st.warning("Chưa có đề thi nào. Vui lòng báo giáo viên.")
        return

    is_submitted = st.session_state.get("quiz_submitted", False)
    doing_quiz = st.session_state.get("doing_quiz", False)

    # 1. KHU VỰC ĐĂNG NHẬP / BẮT ĐẦU LÀM BÀI
    if not is_submitted and not doing_quiz:
        st.info("Vui lòng nhập thông tin để bắt đầu.")
        with st.form("student_login_form"):
            # Dùng key khác để tránh xung đột với các phần khác của code
            name = st.text_input("✍️ Nhập Họ và Tên:", key="stu_name_form")
            clas = st.text_input("🏫 Nhập Lớp (VD: 7A1):", key="stu_class_form")
            
            # Nút bắt đầu làm bài nằm trong form
            submitted_login = st.form_submit_button("🚀 Bắt đầu làm bài", type="primary")

        if submitted_login:
            # Lưu thông tin vào session state với key chuẩn
            st.session_state["stu_name"] = name.strip()
            st.session_state["stu_class"] = clas.strip()
            
            if not st.session_state["stu_name"] or not st.session_state["stu_class"]:
                st.error("⚠️ Vui lòng nhập đầy đủ Họ và Tên cùng Lớp.")
                # Xóa thông tin tạm nếu không hợp lệ
                if "stu_name" in st.session_state: del st.session_state["stu_name"]
                if "stu_class" in st.session_state: del st.session_state["stu_class"]
                return

            # Logic khởi tạo bài thi (Xáo trộn câu hỏi và đáp án)
            quiz = [dict(q) for q in quiz_raw]
            random.shuffle(quiz)
            for q in quiz:
                # Chuẩn hóa đáp án trước khi xáo trộn
                norm_opts = []
                # Xử lý trường hợp option có tiền tố A. B. C. D.
                for opt in q["options"]:
                    m = re.match(r"^[A-D][\.\)]\s*(.*)", opt)
                    norm_opts.append(m.group(1).strip() if m else opt.strip())
                
                # Tạo cặp (đáp án, cờ đúng)
                opts_with_flag = [(text, text == q["answer"]) for text in norm_opts]
                random.shuffle(opts_with_flag)
                
                # Cập nhật lại options và answer sau khi xáo trộn
                q["options"] = [t for t, _ in opts_with_flag]
                q["answer"] = next((t for t, flag in opts_with_flag if flag), "")
                
            st.session_state["quiz_data"] = quiz
            st.session_state["start_time"] = datetime.now()
            st.session_state["doing_quiz"] = True
            st.session_state["responses"] = {q["question"]: None for q in quiz}
            st.session_state["quiz_submitted"] = False
            st.rerun()
        return

    # 2. LẤY THÔNG TIN HỌC SINH KHI ĐANG LÀM HOẶC ĐÃ NỘP BÀI
    name = st.session_state.get("stu_name", "")
    clas = st.session_state.get("stu_class", "")

    # 3. HIỂN THỊ THÔNG TIN CHUNG VÀ BÀI THI KHI doing_quiz = True
    if doing_quiz:
        st.markdown("---")
        st.subheader(f"👋 Chào bạn: {name} - Lớp {clas}")
        st.info(f"Đề thi có {len(quiz_raw)} câu hỏi. Thời gian: {DEFAULT_TIME_LIMIT} phút.")
        
        quiz = st.session_state.get("quiz_data", [])
        if not quiz:
            st.error("Lỗi: Không tìm thấy dữ liệu đề thi.")
            st.session_state["doing_quiz"] = False
            return

        # Logic tính thời gian
        start_time = st.session_state.get("start_time", datetime.now())
        elapsed = (datetime.now() - start_time).total_seconds()
        remaining = max(DEFAULT_TIME_LIMIT * 60 - int(elapsed), 0)
        mins, secs = divmod(remaining, 60)
        progress = min(1.0, elapsed / (DEFAULT_TIME_LIMIT * 60))
        st.progress(progress)
        st.markdown(f"⏳ **Thời gian còn lại: {int(mins):02d}:{int(secs):02d}**")

        auto_submit = False
        if remaining == 0:
            st.warning("⏰ Hết giờ! Hệ thống sẽ tự nộp bài.")
            auto_submit = True
            
        
        with st.form("quiz_form"):
            for idx, q in enumerate(quiz, start=1):
                prev_choice = st.session_state["responses"].get(q["question"], None)
                
                # HIỂN THỊ HÌNH ẢNH (NẾU CÓ)
                if q.get("image_base64"):
                    try:
                        image_data = base64.b64decode(q["image_base64"])
                        st.image(image_data, caption=f"Hình ảnh minh họa Câu {idx}", use_column_width="auto")
                    except Exception as e:
                        st.warning(f"Không thể hiển thị hình ảnh cho Câu {idx}.")
                
                try:
                    default_index = q["options"].index(prev_choice)
                except (ValueError, AttributeError):
                    default_index = None

                choice = st.radio(
                    f"**Câu {idx}:** {q['question']}",
                    q["options"],
                    index=default_index,
                    key=f"q_{idx}_radio",
                    label_visibility="visible"
                )
                
                st.session_state["responses"][q["question"]] = choice
                st.write("---")
            
            submitted = st.form_submit_button("✅ Nộp bài", type="primary")

        if auto_submit or submitted:
            score = 0
            total = len(quiz)
            
            # Tính điểm
            for q in quiz:
                chosen = st.session_state["responses"].get(q["question"], None)
                if chosen and chosen == q["answer"]: 
                    score += 1
            
            st.session_state["score"] = score
            percent = round(score / total * 10, 2) if total else 0
            
            st.balloons() 
            st.toast("🎉 Bạn đã hoàn thành bài thi! Chúc mừng!")
            
            # Lưu vào SCORES_FILE
            try:
                if os.path.exists(SCORES_FILE):
                    df = pd.read_excel(SCORES_FILE)
                    if df.columns.tolist() != EXPECTED_COLUMNS:
                        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
                else:
                    df = pd.DataFrame(columns=EXPECTED_COLUMNS)
                    
                new_row = {
                    "Tên Học Sinh": name,
                    "Lớp": clas,
                    "Điểm": score,
                    "Tổng Số Câu": total,
                    "Thời Gian Nộp Bài": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_excel(SCORES_FILE, index=False)
            except Exception as e:
                st.error(f"Lưu kết quả thất bại: {e}")

            st.session_state["quiz_submitted"] = True 
            st.session_state["doing_quiz"] = False
            
            st.success(f"Điểm số: {score}/{total} ({percent} điểm).")
            time.sleep(2)
            st.rerun()
        
        # Tự động refresh để đếm giờ
        if remaining > 0 and not submitted:
            time.sleep(1)
            st.rerun()
        return

    # 4. HIỂN THỊ KẾT QUẢ VÀ ĐÁP ÁN (Chế độ Ôn tập)
    if is_submitted and not doing_quiz:
        st.markdown("---")
        st.subheader("🔍 Chế độ Ôn tập & Xem Đáp án")
        score = st.session_state.get('score', 0)
        total = len(st.session_state.get('quiz_data', []))
        percent = round(score / total * 10, 2) if total else 0
        
        st.success(f"Điểm số: **{score}/{total}** ({percent} điểm)")

        quiz = st.session_state.get("quiz_data", [])
        
        with st.container():
            for idx, q in enumerate(quiz, start=1):
                correct_answer = q['answer']
                student_choice = st.session_state["responses"].get(q["question"])
                is_correct = student_choice == correct_answer
                
                # HIỂN THỊ HÌNH ẢNH (NẾU CÓ)
                if q.get("image_base64"):
                    try:
                        image_data = base64.b64decode(q["image_base64"])
                        st.image(image_data, caption=f"Hình ảnh minh họa Câu {idx}", use_column_width="auto")
                    except Exception as e:
                        st.warning(f"Không thể hiển thị hình ảnh cho Câu {idx}.")

                feedback_icon = "✅" if is_correct else "❌"
                
                st.markdown(f"**{feedback_icon} Câu {idx}:** {q['question']}", unsafe_allow_html=True)
                
                # Hiển thị các lựa chọn với màu sắc và ký hiệu
                for option in q['options']:
                    html_content = option
                    is_correct_option = (option == correct_answer)
                    is_student_chosen = (option == student_choice)
                    
                    style_attributes = "padding: 5px; margin-bottom: 3px; border-radius: 5px; border: 1px solid #eee; margin-left: 20px;"
                    icon_prefix = ""

                    if is_correct_option:
                        style_attributes = "background-color: #e6ffe6; border-color: green; font-weight: bold; padding: 5px; margin-bottom: 3px; border-radius: 5px; margin-left: 20px;"
                        icon_prefix = "✅ "
                        
                    if is_student_chosen and not is_correct_option:
                        style_attributes = "background-color: #ffe6e6; border-color: red; font-weight: bold; padding: 5px; margin-bottom: 3px; border-radius: 5px; margin-left: 20px;"
                        icon_prefix = "❌ "
                    elif is_student_chosen and is_correct_option:
                         style_attributes = "background-color: #ccffcc; border-color: green; font-weight: bold; padding: 5px; margin-bottom: 3px; border-radius: 5px; margin-left: 20px;"
                         icon_prefix = "✅ "

                    
                    final_text = f"<div style='{style_attributes}'>{icon_prefix}{html_content}</div>"
                    st.markdown(final_text, unsafe_allow_html=True)
                        
                st.markdown("---")
                
        # Nút bắt đầu bài thi mới
        if st.button("🚀 Bắt đầu Bài thi mới", key="start_new_quiz_btn", type="primary"):
            # Xóa toàn bộ session state liên quan đến bài thi
            for key in ["quiz_data", "responses", "start_time", "doing_quiz", "quiz_submitted", "score", "stu_name", "stu_class", "stu_name_form", "stu_class_form"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
        
        return 
        
# =========================================================================
# ====== Giao diện Giáo viên (GIỮ NGUYÊN) ======
# =========================================================================
def admin_ui():
    
    def delete_scores_file():
        """Xóa file scores.xlsx và khởi tạo lại file rỗng."""
        try:
            if os.path.exists(SCORES_FILE):
                os.remove(SCORES_FILE)
            init_scores_file() # Khởi tạo lại file rỗng với header
            st.success("🗑️ **Đã xóa toàn bộ bảng điểm thành công!**")
            # Xóa các biến liên quan đến quiz trong session state
            if 'admin_logged_in' in st.session_state: del st.session_state.admin_logged_in
            if 'uploaded_quiz_data' in st.session_state: del st.session_state.uploaded_quiz_data
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Lỗi khi xóa file bảng điểm: {e}")
            
    # Xóa dữ liệu quiz khi đăng xuất
    if not st.session_state.get("admin_logged_in", False):
        if 'uploaded_quiz_data' in st.session_state: del st.session_state.uploaded_quiz_data
        
    # (Đăng nhập/Đăng xuất giữ nguyên)
    if not st.session_state.get("admin_logged_in", False):
        st.info("🔐 Đăng nhập để truy cập khu vực Giáo viên")
        pwd = st.text_input("Nhập mật khẩu:", type="password")
        if st.button("Đăng nhập", type="primary"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Sai mật khẩu! Thử lại.")
        return

    st.success("✅ Bạn đã đăng nhập vào khu vực Giáo viên.")
    if st.button("🚪 Đăng xuất"):
        st.session_state.admin_logged_in = False
        st.rerun()

    st.header("👨‍🏫 Bảng Điều Khiển Giáo Viên")
    st.subheader("1️⃣ Cấu hình & Thời gian thi")
    if 'time_limit' not in st.session_state:
        st.session_state.time_limit = DEFAULT_TIME_LIMIT
        
    time_limit = st.number_input("⏱️ Giới hạn thời gian (phút):", 5, 180, st.session_state.time_limit, step=5)
    st.session_state.time_limit = time_limit

    # Khu vực tải file và đọc đề
    st.subheader("2️⃣ Tải Đề Thi (Word)")
    up = st.file_uploader("📄 Chọn file .docx", type=["docx"])
    
    # Logic xử lý file Word (Giữ nguyên logic chính)
    if up:
        try:
            q = load_quiz_from_word(up)
            if q:
                st.success(f"Đã đọc **{len(q)}** câu hỏi hợp lệ. **Vui lòng kiểm tra và chỉnh sửa trước khi Lưu.**")
                # Lưu vào session state
                st.session_state.uploaded_quiz_data = q
                
            else:
                st.error("Không đọc được dữ liệu trong file này hoặc không có câu hỏi hợp lệ.")
                if 'uploaded_quiz_data' in st.session_state: del st.session_state.uploaded_quiz_data
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")
            
    
    # --------------------------------------------------------
    # CHỨC NĂNG CHỈNH SỬA ĐỀ THI VỚI ẢNH (GIỮ NGUYÊN)
    # --------------------------------------------------------
    if 'uploaded_quiz_data' in st.session_state and st.session_state.uploaded_quiz_data:
        quiz_data = st.session_state.uploaded_quiz_data
        st.subheader(f"3️⃣ Chỉnh Sửa & Lưu Đề Thi ({len(quiz_data)} câu)")
        
        with st.form("edit_quiz_form"):
            
            # Khởi tạo một list mới để lưu dữ liệu đã chỉnh sửa
            new_quiz_data = [] 
            
            for idx, q in enumerate(quiz_data, 1):
                st.markdown(f"**--- Câu {idx} ---**")
                
                # 1. Chỉnh sửa nội dung câu hỏi
                edited_question = st.text_area(
                    f"Nội dung Câu {idx}:",
                    value=q['question'],
                    key=f"q_{idx}_text",
                    height=70
                )
                
                # 2. Chỉnh sửa các lựa chọn và xác định đáp án đúng
                option_letters = ["A", "B", "C", "D"]
                edited_options = []
                correct_letter = None
                
                # Tìm đáp án đúng hiện tại để đặt làm mặc định cho radio button
                try:
                    current_correct_answer_index = q['options'].index(q['answer'])
                    current_correct_letter = option_letters[current_correct_answer_index]
                except ValueError:
                    current_correct_letter = option_letters[0]
                    
                # Vùng nhập liệu cho các lựa chọn
                cols = st.columns(2)
                for i, opt_letter in enumerate(option_letters):
                    col = cols[i % 2]
                    opt_content = col.text_input(
                        f"Lựa chọn {opt_letter}:",
                        value=q['options'][i],
                        key=f"q_{idx}_opt_{opt_letter}"
                    )
                    edited_options.append(opt_content)
                
                # Radio button xác định đáp án đúng
                chosen_correct_letter = st.radio(
                    f"**Đáp án đúng Câu {idx}:**",
                    options=option_letters,
                    index=option_letters.index(current_correct_letter),
                    key=f"q_{idx}_correct_radio",
                    horizontal=True
                )
                
                # 3. Tải lên/Xem trước Hình ảnh
                current_img_data = q.get("image_base64")
                if current_img_data:
                    with st.expander(f"🖼️ Hình ảnh hiện tại (Câu {idx})"):
                        try:
                            img_bytes = base64.b64decode(current_img_data)
                            st.image(img_bytes, caption="Hình ảnh đang được lưu", use_column_width="auto")
                        except:
                            st.warning("Không thể giải mã hình ảnh hiện tại.")

                uploaded_file = st.file_uploader(
                    f"⬆️ Tải lên hình ảnh mới (Câu {idx})", 
                    type=["png", "jpg", "jpeg"], 
                    key=f"q_{idx}_img_upload"
                )

                new_img_base64 = current_img_data
                if uploaded_file is not None:
                    # Lưu file ảnh mới vào base64
                    bytes_data = uploaded_file.read()
                    new_img_base64 = base64.b64encode(bytes_data).decode('utf-8')
                    st.success("Đã tải lên hình ảnh mới! Bấm Lưu để cập nhật.")
                    st.image(bytes_data, caption="Hình ảnh mới", width=200)
                
                # 4. Gộp dữ liệu đã chỉnh sửa
                new_question = {
                    "question": edited_question.strip(),
                    "options": [o.strip() for o in edited_options],
                    "answer": edited_options[option_letters.index(chosen_correct_letter)].strip(),
                    "image_base64": new_img_base64 # Lưu dữ liệu hình ảnh
                }
                new_quiz_data.append(new_question)
                st.markdown("---")
            
            # Nút Lưu (Đặt bên ngoài vòng lặp nhưng trong form)
            save_button = st.form_submit_button("💾 Lưu Đề Thi Đã Chỉnh Sửa", type="primary")

        if save_button:
            # Kiểm tra lại dữ liệu trước khi lưu
            valid_quiz_count = sum(1 for q in new_quiz_data if q['question'] and len(q['options']) == 4 and q['answer'] in q['options'])
            
            if valid_quiz_count == len(new_quiz_data):
                # Lưu đề thi vào file JSON
                save_quiz(new_quiz_data)
                
                # Dọn dẹp session state sau khi lưu
                del st.session_state.uploaded_quiz_data
                st.rerun()
            else:
                st.error("⚠️ **Lỗi:** Có câu hỏi không hợp lệ (thiếu nội dung, thiếu lựa chọn, hoặc đáp án không khớp). Vui lòng kiểm tra lại.")

    # --------------------------------------------------------
    # KHU VỰC BẢNG ĐIỂM (4) và XÓA BẢNG ĐIỂM (5) - (GIỮ NGUYÊN)
    # --------------------------------------------------------
    st.subheader("4️⃣ Xem & Tải Bảng Điểm")
    
    if os.path.exists(SCORES_FILE) and os.path.getsize(SCORES_FILE) > 0:
        try:
            df = pd.read_excel(SCORES_FILE)
            if not df.empty:
                df["% Điểm (Thang 10)"] = round(df["Điểm"] / df["Tổng Số Câu"] * 10, 2)
                st.dataframe(df, use_container_width=True)
                out = BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as w:
                    df.to_excel(w, index=False)
                st.download_button("📥 Tải Bảng Điểm", out.getvalue(),
                    file_name=f"BangDiem_{dt.date.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Chưa có kết quả nào.")
        except Exception as e:
            st.error(f"Lỗi khi đọc file bảng điểm hoặc tạo file tải xuống: {e}")
            
    else:
        st.info("Chưa có file bảng điểm.")
        
    st.markdown("---")
    
    st.subheader("5️⃣ Xóa Dữ Liệu Bảng Điểm")
    
    with st.expander("⚠️ **Bấm vào đây để Xóa Toàn Bộ Bảng Điểm**"):
        st.warning("Bạn có chắc chắn muốn xóa toàn bộ dữ liệu kết quả thi? Hành động này không thể hoàn tác.")
        
        if st.button("❌ Vâng, XÓA BẢNG ĐIỂM VĨNH VIỄN", type="secondary"):
            delete_scores_file()
            
# ====== Điều hướng chính (GIỮ NGUYÊN) ======
def main():
    if "mode" not in st.session_state:
        st.session_state.mode = "student"
        
    with st.sidebar:
        st.sidebar.markdown(
    """
    <h3 style='text-align: center; color: #444; font-weight: 800;'>
        Trường THCS Mỹ Hòa
    </h3>
    <hr style='margin-top: -10px; margin-bottom: 10px;'>
    """,
    unsafe_allow_html=True
)

        st.header("⚙️ Chế độ Ứng dụng")
        mode = st.radio("Chọn chế độ:", ["Học sinh", "Giáo viên"], index=0 if st.session_state.mode == "student" else 1)
        st.session_state.mode = "student" if mode == "Học sinh" else "admin"

    if st.session_state.mode == "student":
        student_ui()
    else:
        admin_ui()

if __name__ == "__main__":
    main()