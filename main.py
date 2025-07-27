"""
SEC EDGAR Filings MCP Server
This server, built on FastMCP, provides tools for downloading SEC filings,
converting HTML to PDF, and transforming PDF to Markdown for LLM processing.
"""

import sys
import requests
import re
import logging
from pathlib import Path
from typing import Optional
import time
import traceback
from mcp.server.fastmcp import FastMCP
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode


# Initialize MCP server 
mcp = FastMCP("SEC EDGAR MCP Server", version="0.1.0", request_timeout=3000) 

# ===== Task 1: PDF to Markdown Conversion =====

@mcp.tool()
def read_as_markdown(input_file_path: str) -> str:
    """
    Convert a PDF file to Markdown (Docling REFERENCED mode).
    
    Args:
        input_file_path: Relative path to PDF in the "pdf/" folder.
    
    Returns:
        For small files: Markdown text.
        For large files: Completion message with results file.
    """
    try:
        pdf_dir = Path("/app/pdf")
        file_path = pdf_dir / input_file_path

        if not file_path.exists():
            return f"Error: File not found: {input_file_path}"
        
        markdown_dir = Path("/app/markdown")
        pdf_stem = Path(input_file_path).stem
        md_path = markdown_dir / f"{pdf_stem}.md"
        
        if md_path.exists():
            return f"Markdown file already exists: {md_path.name}. File has already been converted."
        
        # Check if the file is too large(0.5MB)
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        large_file_threshold_mb = 0.5
        
        # Convert IMAGE in PDF to Markdown
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = True

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        result = converter.convert(str(file_path))
        doc = result.document
        
        markdown_dir.mkdir(exist_ok=True)
        images_dir = Path("/app/extracted_images") / pdf_stem
        images_dir.mkdir(parents=True, exist_ok=True)

        # Save Markdown with IMAGE in PDF
        doc.save_as_markdown(
            filename=str(md_path),
            artifacts_dir=images_dir,
            image_mode=ImageRefMode.REFERENCED
        )
        
        print(f"[DEBUG] Images saved to: {images_dir}", file=sys.stderr)
        print(f"[DEBUG] Markdown saved to: {md_path}", file=sys.stderr)
        
        # Branch: Return just result message for large files
        if size_mb >= large_file_threshold_mb:
            return (f"PDF is large ({size_mb:.1f}MB). Conversion completed.\n"
                    f"Result file: {md_path.name}\n"
                    "Use read_markdown_file() to read the contents.")
        
        # Branch: Return Markdown directly for small files
        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        return markdown_content

    except Exception as e:
        return f"Error during Markdown conversion: {str(e)}"
    
@mcp.tool()
def read_markdown_file(markdown_filename: str, start_char: int = 0, length: int = 50000) -> str:
    """
    Reads a specific portion of a saved Markdown file.

    Args:
        markdown_filename: The name of the Markdown file (e.g., "test.md")
        start_char: The starting character position to read from (default: 0)
        length: The number of characters to read (default: 50000)

    Returns:
        The Markdown text within the specified range
    """
    try:
        markdown_dir = Path("/app/markdown")
        md_path = markdown_dir / markdown_filename
        
        if not md_path.exists():
            return f"Error: Markdown file not found: {markdown_filename}"
        
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        total_length = len(content)
        end_char = min(start_char + length, total_length)
        excerpt = content[start_char:end_char]
        
        return f""" File: {markdown_filename}
Total size: {total_length:,} characters
Reading: chars {start_char:,} - {end_char:,}

{excerpt}

{'...[End of file]' if end_char >= total_length else '...[More content available]'}"""
        
    except Exception as e:
        return f"Error reading markdown file: {str(e)}"


# ===== Task 2: HTML to PDF Conversion =====

@mcp.tool()
async def html_to_pdf(input_file_path: str, output_file_path: str) -> str:
    """
    Converts an HTML/iXBRL file to PDF.

    Args:
        input_file_path: Relative path to the HTML file (under the "html/" directory).
        output_file_path: Path for the generated PDF file (under the "pdf/" directory).

    Returns:
        Conversion result message.

    Example:
        html_to_pdf("amzn_2024_8_k/amzn-20241031.htm", "amzn_2024_8_k.pdf")
    """
    try:
        html_dir = Path("/app/html")
        pdf_dir = Path("/app/pdf")
        
        input_path = html_dir / input_file_path
        output_path = pdf_dir / output_file_path
        
        if not input_path.exists():
            return f"Error: HTML file not found: {input_file_path}"
        
        if output_path.exists():
            return f"PDF file already exists: {output_file_path}. 이미 변환된 파일이 있습니다."
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            file_url = f"file://{input_path.absolute()}"
            await page.goto(file_url)
            
            await page.pdf(
                path=str(output_path),
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'}
            )
            
            await browser.close()
        
        return f"Successfully converted HTML to PDF: {output_file_path}"
        
    except Exception as e:
        return f"Error converting HTML to PDF: {str(e)}"



# ===== Task3: SEC EDGAR Filing Download Tool =====

@mcp.tool()
def download_sec_filing(cik: str, year: int, filing_type: str, output_dir_path: str) -> str:
    """
    Downloads a specific company's filing from SEC EDGAR.

    Args:
        cik: The company's CIK (Central Index Key) number
        year: The year of the filing to download (2021-2025)
        filing_type: The type of filing ("8-K", "10-Q", "10-K", "DEF 14A")
        output_dir_path: The directory path to save the downloaded files (relative to the html/ folder)

    Returns:
        The path to the main downloaded filing file

    Example:
        download_sec_filing("1018724", 2024, "8-K", "amzn_2024_8_k")
    """
    try:
        # Check Input Validity
        if not (2021 <= year <= 2025):
            return f"Error: Year {year} not supported (only 2021-2025)"
        
        cik_int = int(cik)
        cik_padded = f"{cik_int:010d}"
        
        allowed_types = ["8-K", "10-Q", "10-K", "DEF 14A"]
        if filing_type not in allowed_types:
            return f"Error: filing_type must be one of {allowed_types}"
        
        # Check if the download folder already exists
        html_dir = Path("/app/html")
        output_dir = html_dir / output_dir_path
        if output_dir.exists():
            return f"Download folder already exists: {output_dir_path}. 이미 다운로드된 폴더가 있습니다."
        
        # SEC JSON submissions feed URL
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        
        headers = {
            "User-Agent": "YourName your_email@example.com",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        }
        
        # Wait for a certain period before making the request: SEC 10req/sec limit compliance
        time.sleep(0.15)
        resp = requests.get(submissions_url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return f"Error: Failed to fetch submissions JSON, status {resp.status_code}"
        
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        
        form_types = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])
        filings_accession_numbers = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])
        
        matched_filings = []
        for i in range(len(form_types)):
            form = form_types[i]
            cmp_form = form.replace(" ", "").upper()
            cmp_target = filing_type.replace(" ", "").upper()
            
            if cmp_form != cmp_target:
                continue
                
            rd = report_dates[i]
            if not rd.startswith(str(year)):
                continue
            matched_filings.append(i)
        
        if not matched_filings:
            return f"No filings found for cik={cik_padded}, year={year}, type={filing_type}"
        
        # Sort the matched filings by filing date in descending order
        matched_filings_sorted = sorted(
            matched_filings,
            key=lambda i: filing_dates[i],
            reverse=True
        )
        idx = matched_filings_sorted[0]
        
        acc_num = filings_accession_numbers[idx].replace("-", "")
        primary_doc = primary_docs[idx]
        
        # Prepare the download folder (html/ prefix handling)
        if output_dir_path.startswith("html/"):
            dir_path = output_dir_path[5:]  
        else:
            dir_path = output_dir_path
        
        html_dir = Path("/app/html") / dir_path
        html_dir.mkdir(parents=True, exist_ok=True)
        
        cik_numeric = str(int(cik))
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{acc_num}"
        
        primary_url = f"{base_url}/{primary_doc}"
        
        headers_download = {"User-Agent": "YourName your_email@example.com"}
        
        def download_file(url, target_path):
            time.sleep(0.15)
            resp = requests.get(url, headers=headers_download, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"Failed to download {url} status {resp.status_code}")
            with open(target_path, "wb") as f:
                f.write(resp.content)
        
        primary_filename = primary_doc.replace("/", "_")
        primary_file_path = html_dir / primary_filename
        download_file(primary_url, primary_file_path)
        
        # Try to download related files
        related_exts = [".xsd", "_pre.xml", "_lab.xml", ".xml", ".htm", ".html", ".hdr", ".txt"]
        prefix = Path(primary_filename).stem
        
        for ext in related_exts:
            related_file = prefix + ext
            if related_file == primary_filename:
                continue
            related_url = f"{base_url}/{related_file}"
            target_path = html_dir / related_file
            try:
                download_file(related_url, target_path)
            except Exception:
                pass
        
        # Download additional images from HTML files
        try:
            with open(primary_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # If the main document is in HTML format, find the '<img>' tag inside and collect the image path.    
            img_pattern = r'<img[^>]+src=["\']([^"\']+\.(jpg|jpeg|png|gif|svg|bmp))["\'][^>]*>'
            img_matches = re.findall(img_pattern, html_content, re.IGNORECASE)

            for img_match in img_matches:
                img_filename = img_match[0]
                if not img_filename.startswith(('http://', 'https://', '//')):
                    img_url = f"{base_url}/{img_filename}"
                    img_target_path = html_dir / img_filename
                    try:
                        download_file(img_url, img_target_path)
                    except Exception:
                        pass
        except Exception:
            pass
        
        # Return the path in the required format
        if output_dir_path.startswith("html/"):
            result_path = f"{output_dir_path}/{primary_filename}"
        else:
            result_path = f"html/{output_dir_path}/{primary_filename}"
        return result_path
    
    except Exception as e:
        return f"Error in download_sec_filing: {str(e)}"

if __name__ == "__main__":
    print("Starting SEC EDGAR MCP Server")
    print("Use Ctrl+C to stop the server")
    
    mcp.run()



