# SEC EDGAR Filings MCP Server

A Model Context Protocol (MCP) server that enables AI agents to download, convert, and analyze SEC EDGAR filings. Built with FastMCP, this server provides tools for downloading SEC filings, converting HTML to PDF, and transforming PDF documents to Markdown for LLM processing.

## Features

### Core MCP Tools

1. **`read_as_markdown`** - Convert PDF files to Markdown using Docling <br>
  1-2. **`read_markdown_file`** - List files, read large markdown files in chunks
2. **`html_to_pdf`** - Convert HTML/iXBRL files to PDF using Playwright
3. **`download_sec_filing`** - Download SEC EDGAR filings by CIK, year, and filing type
4. Set the three MCP Tools that you created to work with Cloud Desktop.


### Key Capabilities

- **SEC EDGAR Integration**: Direct download from SEC's official API
- **Document Processing**: Complete pipeline from HTML → PDF → Markdown
- **Docker Ready**: One-command setup with volume mounting
- **Claude Desktop Compatible**: Pre-configured for immediate use
- **Rate Limiting**: Complies with SEC's 10 requests/second limit
- **Image Extraction**: Automatically extracts and references images from documents

## Requirements

- Docker (recommended) 
- Claude Desktop for MCP client testing

## Start with Docker

### 1. Build the Docker Image

```bash
docker build -t deepauto-mcp .
```

### 2. Configure Claude Desktop

Update your Claude Desktop configuration file.

Replace `{AbsolutePath}` with your actual project path.

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sec-edgar": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--volume",
        "/{AbsolutePath}/app/pdf:/app/pdf",
        "--volume",
        "/{AbsolutePath}/app/html:/app/html",
        "--volume",
        "/{AbsolutePath}/app/markdown:/app/markdown",
        "--volume",
        "/{AbsolutePath}/app/extracted_images:/app/extracted_images",
        "deepauto-mcp"
      ],
      "env": {}
    }
  }
}
```


### 3. Restart Claude Desktop

Close and reopen Claude Desktop to load the MCP server.



### 4. Example Usage Workflow

Here's a complete example prompt for Claude Desktop:

```
From downloading SEC EDGAR public files to Markdown conversion, please do the following in order. If the contents are in the folder when creating files, do not create them.

1. First, download the latest public HTML file of CIK 1018724, Year 2024, Form DEF 14A type from SEC EDGAR.

2. Converts downloaded HTML files to PDFs.

3. Convert the converted PDF file to Markdown.
Check the PDF size and wait for the Markdown text return if the size is small.
If the size is large, the Markdown text will not output immediately, and the conversion will take a long time, so wait and see the file in /markdown.

4. All steps run sequentially, and if the file is small, please wait for the Markdown conversion to complete. Avoid additional commands before completing.
```

## API Documentation

### 1. read_as_markdown

Converts PDF files to Markdown using Docling.

```python
read_as_markdown(
    input_file_path: str,    # PDF file path in pdf/ folder
)
```

**Example**:
```
read_as_markdown("amzn_2024_8k.pdf")
```

**Features**:
- Extracts images with proper references
- Handles large files by saving to file
- Returns content directly for small files
- Creates structured markdown with tables and formatting

### 1-2. read_markdown_file
```python
read_markdown_file(
    markdown_filename: str, # Filename in markdown/ folder
    start_char: int = 0,    # Starting character position
    length: int = 50000     # Number of characters to read
)
```

### 2. html_to_pdf

Converts HTML/iXBRL files to PDF using Playwright.

```python
html_to_pdf(
    input_file_path: str,  # Relative path in html/ folder
    output_file_path: str  # Output path in pdf/ folder
)
```

**Example**:
```
html_to_pdf("amzn_2024_8k/amzn-20241031.htm", "amzn_2024_8k.pdf")
```

### 3. download_sec_filing

Downloads SEC EDGAR filings for a specific company.

```python
download_sec_filing(
    cik: str,           # Company's CIK number (e.g., "1018724" for Amazon)
    year: int,          # Filing year (2021-2025)
    filing_type: str,   # "8-K" | "10-Q" | "10-K" | "DEF 14A"
    output_dir_path: str # Output directory path (e.g., "amzn_2024_8k")
)
```

**Example**:
```
download_sec_filing("1018724", 2024, "8-K", "amzn_2024_8k")
```

**Returns**: Path to the main HTML filing (e.g., `html/amzn_2024_8k/amzn-20241031.htm`)


## Project Structure

```
deepauto_mcp/
├── main.py                     # MCP server implementation
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── claude_desktop_config.json  # Claude Desktop MCP config
├── README.md                   # This file
└── app/                        # Data directories (mounted as volumes)
    ├── pdf/                    # PDF files
    ├── html/                   # HTML/iXBRL files
    ├── markdown/               # Generated Markdown files
    └── extracted_images/       # Extracted images from documents
```


## Testing

### Test Files

The project has been tested with these SEC filings:

- **8-K**: Amazon.com Inc. - Form 8-K. 2024-05-14.pdf
- **10-Q**: Amazon.com Inc. - Form 10-Q. For the Fiscal Quarter Ended 2025-03-31.pdf
- **10-K**: Amazon.com Inc. - Form 10-K. For the Fiscal Year Ended 2024-12-31.pdf
- **DEF 14A**: Amazon.com Inc. - Form DEF 14A. Definitive Proxy Statement.pdf

### Sample Test Commands

1. **Download a filing**:
   ```
   download_sec_filing("1018724", 2024, "8-K", "test_download")
   ```

2. **Convert to PDF**:
   ```
   html_to_pdf("test_download/main_file.htm", "test_output.pdf")
   ```

3. **Convert to Markdown**:
   ```
   read_as_markdown("test_output.pdf")
   ```

## Configuration

### SEC API Compliance

- Implements 10 requests/second rate limiting
- Uses proper User-Agent headers
- Follows SEC EDGAR access guidelines

## Troubleshooting


### Limitations

1. **Image Reprocessing**: When converting HTML to PDF and then to Markdown, images are regenerated rather than reused from the original HTML download. Failed to extract the original file name of the image downloaded to HTML. When PDF→Markdown is converted, the image is recreated and stored in `extracted_images/` directory.

2. **Table of Contents Recognition**: Some `Table of Contents` sections are incorrectly recognized as images during PDF processing. 


## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Docker and volume mount configurations
3. Verify Claude Desktop MCP setup
4. Test individual MCP tools

---

**Built with FastMCP for seamless AI agent integration**
