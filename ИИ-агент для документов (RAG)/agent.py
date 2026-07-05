import os
import shutil
import re
import time
import pandas as pd
from difflib import SequenceMatcher
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_deepseek import ChatDeepSeek
from langchain_classic.chains import RetrievalQA
import warnings
warnings.filterwarnings("ignore")

API_KEY = "sk-361ab63600554d578b0ed61c88be77eb"
SOURCE_FOLDER = r"C:\Users\zakharianag\Desktop\Кусты"
WORK_FOLDER = r"C:\Users\zakharianag\Desktop\Кусты_Упорядочено"
DB_FOLDER = "doc_db"
SIMILARITY_THRESHOLD = 0.75
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

FIXED_CATEGORIES = {
    "Акты": ["акт", "приемка", "сдача", "выполнен", "освидетельствование"],
    "Суточные_рапорты": ["суточный рапорт", "суточный отчёт", "daily report"],
    "Анализ_МСП": ["мсп", "анализ мсп", "механическая скорость"],
    "Геология": ["геолог", "разрез", "стратиграфия"],
    "Техническая_документация": ["проект", "схема", "план", "спецификация"],
    "Договоры": ["договор", "контракт", "соглашение"],
}

def clean_name(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[^а-яА-Яa-zA-Z ]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name

def group_files_by_name(folder_path):
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if not f.startswith('~$'):
                all_files.append(os.path.join(root, f))
    groups, used = {}, set()
    for file_path in all_files:
        if file_path in used: continue
        filename = os.path.basename(file_path)
        clean = clean_name(filename)
        if not clean: clean = "Разное"
        group = [file_path]
        for other_path in all_files:
            if other_path == file_path or other_path in used: continue
            other_clean = clean_name(os.path.basename(other_path))
            if not other_clean: other_clean = "Разное"
            similarity = SequenceMatcher(None, clean, other_clean).ratio()
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(other_path)
                used.add(other_path)
        best_name = max(group, key=lambda x: len(clean_name(os.path.basename(x))))
        folder_name = clean_name(os.path.basename(best_name)).replace(' ', '_').capitalize()
        if len(folder_name) > 40: folder_name = folder_name[:40]
        groups[folder_name] = group
        used.add(file_path)
    return groups

def sort_files():
    print(f"🔍 Сканирую: {SOURCE_FOLDER}")
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Папка не найдена: {SOURCE_FOLDER}")
        return
    groups = group_files_by_name(SOURCE_FOLDER)
    total_copied = 0
    for folder_name, file_list in groups.items():
        dest_folder = os.path.join(WORK_FOLDER, folder_name)
        os.makedirs(dest_folder, exist_ok=True)
        for src_path in file_list:
            filename = os.path.basename(src_path)
            dest_path = os.path.join(dest_folder, filename)
            counter = 1
            name, ext = os.path.splitext(filename)
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext}")
                counter += 1
            try:
                shutil.copy2(src_path, dest_path)
                total_copied += 1
                time.sleep(0.05)
            except Exception as e:
                print(f"   ❌ {filename}: {e}")
    print(f"\n✅ Готово! Скопировано {total_copied} файлов в {len(groups)} папок.")
    print(f"📂 Результат: {WORK_FOLDER}")
    print("🔒 ОРИГИНАЛЬНЫЕ ФАЙЛЫ НЕ ТРОНУТЫ!")

def index_documents():
    print("📚 Быстрая индексация...")
    docs = []
    for root, dirs, files in os.walk(WORK_FOLDER):
        for file in files:
            path = os.path.join(root, file)
            cat = os.path.basename(os.path.dirname(path))
            try:
                if file.endswith('.pdf'):
                    loader = PyPDFLoader(path)
                    for d in loader.load():
                        d.metadata.update({"category": cat, "filename": file})
                        docs.append(d)
                elif file.endswith('.docx'):
                    loader = Docx2txtLoader(path)
                    for d in loader.load():
                        d.metadata.update({"category": cat, "filename": file})
                        docs.append(d)
                elif file.endswith(('.xlsx','.xls','.csv')):
                    df = pd.read_excel(path) if not path.endswith('.csv') else pd.read_csv(path)
                    text = f"Файл: {file}\nКатегория: {cat}\nКолонки: {', '.join(df.columns)}\n" + df.head(30).to_string()
                    tpath = path+".tmp"
                    with open(tpath,"w",encoding="utf-8") as f: f.write(text)
                    loader = TextLoader(tpath, encoding="utf-8")
                    for d in loader.load():
                        d.metadata.update({"category": cat, "filename": file})
                        docs.append(d)
                    os.remove(tpath)
                elif file.endswith('.txt'):
                    loader = TextLoader(path, encoding="utf-8")
                    for d in loader.load():
                        d.metadata.update({"category": cat, "filename": file})
                        docs.append(d)
            except: pass
    if not docs:
        print("❌ Нет документов для индексации")
        return None
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"🧠 Векторизация {len(chunks)} фрагментов...")
    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vs = Chroma.from_documents(chunks, emb, persist_directory=DB_FOLDER)
    print("✅ Индексация завершена")
    return vs

def ask_questions(vs):
    if not vs: return
    llm = ChatDeepSeek(model="deepseek-chat", api_key=API_KEY, temperature=0.3)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=vs.as_retriever(search_kwargs={"k": 5}))
    print("\n🤖 Задайте вопрос (выход для выхода)")
    while True:
        q = input("\n❓ ").strip()
        if q.lower() in ["выход","exit","quit","стоп"]: break
        if not q: continue
        print("🤔 ...")
        try: print(f"🤖 {qa.run(q)}")
        except Exception as e: print(f"❌ {e}")

def main():
    print("🤖 МЕНЕДЖЕР ДОКУМЕНТОВ")
    while True:
        print("\n1. Рассортировать файлы\n2. Индексация\n3. Вопросы\n4. Выход")
        ch = input("👉 ").strip()
        if ch == "1": sort_files()
        elif ch == "2": vs = index_documents()
        elif ch == "3":
            if 'vs' in locals(): ask_questions(vs)
            else: print("❌ Сначала индексация (п.2)")
        elif ch == "4": break

if __name__ == "__main__":
    main()