import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, TextDataset, DataCollatorForLanguageModeling
from pypdf import PdfReader
from pathlib import Path

# === CONFIG ===
MODEL_NAME = "GroNLP/gpt2-medium-italian-embeddings"
PDF_FOLDER = "training_data/libri"
OUTPUT_DIR = "model_finetuned"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + ' '
    return text


def load_all_texts_from_pdfs(directory):
    all_texts = []
    for file in Path(directory).rglob("*.pdf"):
        try:
            text = extract_text_from_pdf(str(file))
            if text and len(text.strip()) > 100:
                all_texts.append(text.strip())
                print(f"[OK] Caricato: {file.name}")
        except Exception as e:
            print(f"[ERRORE] {file.name}: {e}")
    return all_texts


def save_temp_training_file(texts, path="temp_training.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(texts))
    return path


def test_single_pdf():
    files = list(Path(PDF_FOLDER).rglob("*.pdf"))
    if not files:
        print("[!] Nessun PDF trovato in:", PDF_FOLDER)
        return

    max_chars = input("\n🔧 Inserisci il numero massimo di caratteri da tokenizzare (es. 2000): ").strip()
    try:
        max_chars = int(max_chars)
    except:
        max_chars = 2000

    while True:
        print("\n📚 PDF disponibili:")
        for i, f in enumerate(files):
            print(f"[{i}] {f.name}")

        index = input("\nSeleziona il numero del PDF da testare (invio per uscire): ")
        if not index.strip():
            break

        try:
            selected_file = files[int(index)]
            text = extract_text_from_pdf(selected_file)
            print("\n📖 Testo estratto (primi 1000 caratteri):\n")
            print(text[:1000])

            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            tokens = tokenizer.tokenize(text[:max_chars])
            ids = tokenizer.convert_tokens_to_ids(tokens)

            print("\n🔤 Token (primi 250):")
            print(tokens[:250])
            print("\n🧮 Token ID (primi 50):")
            print(ids[:50])
        except Exception as e:
            print("[ERRORE] Durante il test del PDF:", e)


def main():
    print("\nVuoi testare uno o più PDF prima del training? [y/N]")
    scelta = input("> ").strip().lower()
    if scelta == "y":
        test_single_pdf()

    print("\nVuoi usare il dataset mC4 italiano invece dei PDF? [y/N]")
    usa_mc4 = input("> ").strip().lower() == "y"

    print("[1] Caricamento modello e tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)

    if usa_mc4:
        from datasets import load_dataset
        print("[2] Caricamento dataset mC4 da HuggingFace (1%)...")
        dataset = load_dataset("mc4", "it", split="train[:1%]")
        texts = [sample["text"] for sample in dataset if len(sample["text"]) > 200]
    else:
        print("\nAnalizzare l'intera cartella PDF? [y/N]")
        analizza_tutti = input("> ").strip().lower() == "y"
        if analizza_tutti:
            print("[2] Lettura PDF e preparazione testo...")
            texts = load_all_texts_from_pdfs(PDF_FOLDER)
        else:
            print("Nessun dato caricato. Esci o riavvia lo script.")
            return

    training_path = save_temp_training_file(texts)

    print("[3] Tokenizzazione e dataset...")
    dataset = TextDataset(
        tokenizer=tokenizer,
        file_path=training_path,
        block_size=128
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        save_steps=100,
        save_total_limit=2,
        logging_steps=10,
        prediction_loss_only=True
    )

    print("[4] Inizio addestramento...")
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset
    )

    trainer.train()
    print("[5] Modello addestrato salvato in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
