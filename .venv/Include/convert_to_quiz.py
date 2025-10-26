from docx import Document
import re

# ====== ĐƯỜNG DẪN FILE NGUỒN (file gốc Chi đã gửi) ======
source_file = "DE1A-1B-KTGIUAHK1-TIN7.docx"
output_file = "DeA_Tin7_Quiz_Format.docx"

# ====== ĐỌC NỘI DUNG FILE NGUỒN ======
doc = Document(source_file)
text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# ====== TÁCH CÂU HỎI ĐỀ A ======
# tìm vị trí “ĐỀ A” và “ĐỀ B” để lấy phần nội dung của ĐỀ A
match_A = re.search(r"ĐỀ A", text)
match_B = re.search(r"ĐỀ B", text)
if not match_A:
    raise ValueError("Không tìm thấy phần 'ĐỀ A' trong file.")
start = match_A.end()
end = match_B.start() if match_B else len(text)
text_A = text[start:end]

# ====== TÁCH PHẦN ĐÁP ÁN ĐỀ A ======
answers_match = re.search(r"Đáp án đề A[:：]?\s*([\s\S]*?)Đáp án đề B", text)
if not answers_match:
    raise ValueError("Không tìm thấy danh sách đáp án đề A.")
answers_text = answers_match.group(1).strip()

# chuyển "1A 2C 3B..." -> dict {1: "A", 2: "C", 3: "B", ...}
answers = {}
for pair in re.findall(r"(\d+)\s*([ABCD])", answers_text):
    num, ans = int(pair[0]), pair[1].upper()
    answers[num] = ans

# ====== TÁCH CÂU HỎI ======
# Tách theo số câu hỏi
blocks = re.split(r"\n\d+\.", text_A)
questions = []
for i, block in enumerate(blocks[1:], start=1):
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    if len(lines) < 5:
        continue
    question = lines[0]
    options = [l for l in lines[1:5] if re.match(r"^[A-D]\.", l)]
    if not options:
        continue
    correct_letter = answers.get(i, "")
    correct = ""
    if correct_letter in ["A", "B", "C", "D"]:
        idx = ord(correct_letter) - ord("A")
        correct = options[idx][0]  # ví dụ "A"
    questions.append({
        "num": i,
        "question": question,
        "options": options,
        "answer": correct_letter
    })

print(f"✅ Đã tách {len(questions)} câu hỏi ĐỀ A thành công.")

# ====== TẠO FILE WORD MỚI ======
out_doc = Document()
out_doc.add_heading("ĐỀ A – ÔN TẬP GIỮA HỌC KỲ I – TIN HỌC 7", level=1)
out_doc.add_paragraph("")

for q in questions:
    out_doc.add_paragraph(f"{q['num']}. {q['question']}")
    for opt in q["options"]:
        out_doc.add_paragraph(opt)
    out_doc.add_paragraph(f"Đáp án: {q['answer']}")
    out_doc.add_paragraph("")

out_doc.save(output_file)
print(f"📘 File đã được tạo: {output_file}")
