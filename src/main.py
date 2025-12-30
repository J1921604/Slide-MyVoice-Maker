import os
import asyncio
import glob
import argparse

from processor import process_pdf_and_script

async def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="Generate narrated videos (webm) from PDF pages + narration script CSV.",
    )
    parser.add_argument(
        "--input",
        default=os.path.join(base_dir, "input"),
        help="Input directory containing PDF file(s).",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(base_dir, "output"),
        help="Output directory for generated webm files.",
    )
    parser.add_argument(
        "--script",
        default=os.path.join(base_dir, "input", "原稿.csv"),
        help="Narration script CSV path (default: input\\原稿.csv).",
    )
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output
    script_csv_path = args.script

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(script_csv_path):
        print(f"Script CSV file not found: {script_csv_path}")
        print("Please create input\\原稿.csv (columns: index, script).")
        return

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in input directory: {input_dir}")
        return

    for pdf_path in pdf_files:
        await process_pdf_and_script(pdf_path, script_csv_path, output_dir)

if __name__ == "__main__":
    asyncio.run(main())
