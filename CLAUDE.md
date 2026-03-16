# CLAUDE.md

## 1. PROJECT OVERVIEW
- **What this project does**: A full-stack Python web application that evaluates uploaded documents (PDF, Word, or text) via a retrieval-augmented generation (RAG) pipeline and an AI agent to automatically generate a structured due diligence report.
- **Business context**: Built for private equity environments to streamline the due diligence process for alternative assets, automating the extraction and risk analysis of prospective companies.
- **Project goal**: To serve as a flawless, high-quality demonstration piece designed specifically to impress a technical recruiter at a fintech AI startup.

## 2. TECH STACK
Use the following libraries and tools to build out the environment:
- **Gemini 2.0 Flash via google-generativeai SDK**: Serves as the core Large Language Model supplying the agentic capabilities.
- **Google embedding model (models/embedding-001)**: Generates the vector embeddings essential for the RAG pipeline.
- **FAISS**: Provides the in-memory vector storage and executes fast similarity searches for retrieved context.
- **scikit-learn + XGBoost**: Drives the machine learning aspect, including model training, evaluation, and structured inference.
- **FastAPI + uvicorn**: Operates as the high-performance backend API and handles the serving of static frontend files.
- **python-multipart**: Handles reading and parsing of multipart form data for file uploads within FastAPI.
- **PyMuPDF (fitz)**: Extracts plain text efficiently from uploaded PDF data streams.
- **python-docx**: Extracts all paragraph text reliably from uploaded Microsoft Word documents.
- **Jinja2**: Renders the HTML frontend dashboard template explicitly.
- **pandas, numpy**: Processes tabular data structures and generates the synthetic dataset required for training the ML model.
- **joblib**: Serialises the trained XGBoost classifier to disk and deserialises it during active agent inference.
- **pydantic**: Defines strict, type-safe schemas for incoming API requests and outward JSON responses.
- **python-dotenv**: Ingests configuration values securely from local environment variables.
- **Docker + docker-compose**: Containerises the backend, models, and frontend into a single reproducible service.

## 3. FULL PROJECT STRUCTURE
Construct the repository to match the following directory and file architecture exactly:

pe-due-diligence/
├── main.py
├── agent.py
├── rag.py
├── tools.py
├── file_processor.py
├── train.py
├── test_demo.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── static/
│   ├── style.css
│   └── app.js
├── templates/
│   └── index.html
└── data/
    └── sample_novacast.txt

## 4. FILE-BY-FILE SPECIFICATIONS

**train.py**
- **Responsibility**: A standalone script to train and save the investment scoring ML classifier.
- **Implementation specifications**:
  - Write a process that generates a synthetic dataset representing 500 fictional companies using realistic numeric distributions via pandas and numpy.
  - Required dataset features: revenue_growth_pct, ebitda_margin, debt_to_equity, market_size_bn, founding_year, team_size.
  - Required dataset labels: 0 for Pass, 1 for Consider, 2 for Strong Buy.
  - Train an XGBoost classifier on the generated tabular data.
  - Print the overall accuracy and a full classification report to the standard terminal output.
  - Save the completed model to local disk identically as model.pkl using joblib.
  - Ensure documentation notes this script absolutely must be run locally BEFORE docker-compose up is executed.

**file_processor.py**
- **Responsibility**: Standardises and handles the extraction of plain text from varying document types.
- **Implementation specifications**:
  - Create a single FileProcessor class. Have no external knowledge of the RAG pipeline or AI agent orchestrator inside this file.
  - Define a main 'process' method that takes a filename and raw file bytes. It must detect the true file type via the extension and route directly to the appropriate extraction method below, ultimately returning a plain text string.
  - Define an 'extract_from_pdf' method employing PyMuPDF to extract and aggregate all text blocks from the provided byte stream.
  - Define an 'extract_from_docx' method employing python-docx to iterate through document paragraphs and extract all text from the provided byte stream.
  - Define an 'extract_from_txt' method decoding the raw byte stream strictly into a UTF-8 encoded string.
  - Implement a check that deliberately raises a clear, descriptive runtime error if an unsupported file extension is supplied.

**rag.py**
- **Responsibility**: Manages the breaking down of document text, vectorisation, and semantic search capabilities.
- **Implementation specifications**:
  - Create a single RAGPipeline class.
  - Define an ingestion method that accepts text strings and slices them into 500-character chunks, enforcing exactly a 50-character overlap between adjacent chunks.
  - Define a process to embed these plain text chunks identically using the Google embedding model through the generativeai SDK.
  - Instantiate and store these document embeddings in an active FAISS index retained in local memory. Ensure chunks from multiple uploaded documents all feed into this single common index.
  - Define a retrieval method that accepts a plain English query, converts it to an embedding, searches the FAISS index, and returns the top 5 most semantically relevant text chunks as a list of strings.

**tools.py**
- **Responsibility**: Contains standalone business-logic functions that the main agent incorporates as functional tools.
- **Implementation specifications**:
  - Tool 1 (extract_financial_metrics): A function accepting retrieved chunks and a Gemini instance. It must prompt the LLM to inspect the text and forcibly extract six fields (revenue_growth_pct, ebitda_margin, debt_to_equity, market_size_bn, founding_year, team_size) strictly structured as a dictionary. It returns this dictionary.
  - Tool 2 (analyse_risks): A function accepting retrieved chunks and a Gemini instance. It must prompt the LLM to identify the overarching top 5 business risks expressed in the context. It returns these items strictly as a Python list of strings.
  - Tool 3 (predict_investment_score): A function accepting only the metrics dictionary yielded from Tool 1. It must load model.pkl via joblib, format the metrics exactly as the model expects, run live inference, and generate an investment score explicitly mapped out of 100 alongside its respective label (Pass, Consider, or Strong Buy). It returns the score and the label.

**agent.py**
- **Responsibility**: The high-level orchestrator dictating the analytical sequence of events.
- **Implementation specifications**:
  - Create an AgentOrchestrator class.
  - Define a primary execution method accepting a compiled list of text strings representing the uploaded files.
  - Step 1: Concatenate the individual lists of texts together and ingest them via the RAGPipeline instantiation.
  - Step 2: Query the RAG pipeline to pull relevant financial chunks and execute extract_financial_metrics securely.
  - Step 3: Query the RAG pipeline to pull relevant risk chunks and execute analyse_risks securely.
  - Step 4: Pass the outputted financial metrics into predict_investment_score cleanly.
  - Step 5: Gather the metrics, the risks, the score, and all text context, sending it directly to a final Gemini prompt instructing the model to synthesize a cohesive final summary.
  - Build and return a cohesive target dictionary structured cleanly as the DueDiligenceReport. The dictionary must securely feature: company_summary, financial_metrics, risks, investment_score, investment_label, recommendation, and files_analysed (which is just a list of the filenames).

**main.py**
- **Responsibility**: The central ASGI application resolving local API traffic and static routing.
- **Implementation specifications**:
  - Initialize the core FastAPI application to serve the API limits and static frontend layer simultaneously.
  - Mount the local '/static' folder to appropriately serve CSS and custom JS scripts.
  - Configure the local Jinja2 template setup to map accurately to the '/templates' folder.
  - Define a GET route at '/' returning the primary dashboard response via index.html.
  - Define a primary POST route at '/analyse' specifically equipped to intercept multipart file upload boundaries supporting one or more files concurrently. Process each uploaded file securely with the FileProcessor, funnel all strings concurrently to the AgentOrchestrator, and cleanly return the final DueDiligenceReport seamlessly serialised as JSON.
  - Define a GET route at '/health' returning a standard simple ok status block.
  - Write dedicated error handling block catching the unsupported file type exception seamlessly, returning a designated HTTP 400 error containing a user-readable error message.

**templates/index.html**
- **Responsibility**: Defines the structural skeleton of the interactive user interface.
- **Implementation specifications**:
  - Construct a single page layout strictly adopting a dark finance aesthetic. Use Inter or an equivalent modern sans-serif as the sole font.
  - Colour palette: Require deep navy (#0a0e1a) for the document background, #111827 for distinct structural cards, standard white and light grey for typographic contrast, and electric blue (#3b82f6) extensively for accents and key interaction points.
  - Section 1 (Header): Generate a navigation or header block showcasing a small circuit/graph icon alongside the bold text title "PE Due Diligence AI". Embed a smaller subtitle beneath reading "Powered by Gemini 2.0 + ML Scoring".
  - Section 2 (Upload Panel): Build a large, highly visual central drag and drop target zone featuring dashed borders, a prominent icon, and explicit text directing the user to "Drop your documents here". Explicitly list PDF, DOCX, and TXT as supported formats nearby. Underneath it, construct an empty layout ready to populate selected filenames dynamically alongside distinct remove buttons. Provide a full-width "Run Analysis" button flooded in the electric blue accent. Include a visibly hidden loading state containing a smooth animated spinner and the phrase "Agent is analysing documents..." ready for when API calls are transmitting.
  - Section 3 (Results Panel): Initially fully visually hidden. Ensure it is structured to securely hold an Investment Score section configured graphically (e.g. out of 100 on a large numeric readout or gauge), and capable of dynamic color shifts (red for Pass, amber for Consider, green for Strong Buy). Prominently display the text Investment Label below this. Position a Company Summary text block cleanly in its own card layout. Configure a Financial Metrics data grid mapping individual attributes clearly via icons. Construct a designated Risks layout rendering items identically cleanly with warning icon markers. Include a highlighted Recommendation summary block prominently near the bottom. Position small pill-shaped tags up top strictly showing the Files Analysed.

**static/style.css**
- **Responsibility**: Drives the visual presentation across the user experience securely.
- **Implementation specifications**:
  - Declare dark theme color definitions cleanly using standard CSS custom property variables at the root block.
  - Code robust animation keyframes managing smooth entrance transitions for the Results Panel revealing.
  - Craft responsive interactive states making sure the drag and drop border seamlessly glows electric blue upon hover or drag-over.
  - Enforce a layout resilient to various standard laptop display configurations.

**static/app.js**
- **Responsibility**: Governs frontend behaviour, API interactions, and state updates.
- **Implementation specifications**:
  - Intercept native browser events binding exclusively to the designated drag and drop upload zone.
  - Establish a safe array storing user-selected files securely in local memory.
  - Handle rendering logic to visually present these files as internal UI DOM elements equipped with operational remove buttons filtering the array instantly upon click.
  - Hijack the "Run Analysis" button click event, safely wrapping selected files inside a valid multipart FormData object, dispatching it to POST /analyse utilizing the native fetch API.
  - Actively toggle CSS display classes rendering the designated loading spinner instantly as the fetch action occurs.
  - Deconstruct the returned JSON object intelligently mapping values linearly into their respective DOM nodes updating all result sections.
  - Apply logical CSS DOM class manipulation selectively changing the final investment score colors respectively per defined boundaries.
  - Catch network fetch failures mapping UI state safely back to default whilst rendering a friendly text error node notifying the user.

**test_demo.py**
- **Responsibility**: A pure diagnostic integration script completely circumventing the browser.
- **Implementation specifications**:
  - Write a basic synchronous Python script utilizing the requests library directly (no pytest structure).
  - Open data/sample_novacast.txt as a multipart upload cleanly addressing localhost:8000/analyse natively.
  - Pretty print the entirety of the resulting JSON response safely via the terminal ensuring debugging efficiency if the fronted layout introduces bugs.

**data/sample_novacast.txt**
- **Responsibility**: Provide high-quality fixture data that accurately represents the business case.
- **Implementation specifications**:
  - Construct a highly realistic string roughly 400 words detailing a fictional business "NovaCast Industrial", stylized precisely as a formal investment memo.
  - Frame NovaCast as a mid-market UK manufacturing company dealing directly with aerospace and automotive casting parts.
  - Inject explicit numerical intelligence referencing realistic revenue figures, growth percentages, EBITDA margins, total debt load compared to equity, workforce numbers, and broad market sizes.

**Dockerfile**
- **Responsibility**: Instructs the Docker build engine accurately for the unified image layout.
- **Implementation specifications**:
  - Inherit purely from a python:3.11-slim parent base image.
  - Safely issue an apt-get install sequence acquiring necessary system dependencies mandated continuously by the PyMuPDF library.
  - Transfer strictly the required files enabling dependency installation explicitly before application code transfers.
  - Transfer strictly all application codes ensuring static, templates, and root level assets are accurately mapped internally.
  - Intentionally do NOT include an instruction to fire train.py — state model.pkl must exist statically within the context beforehand.
  - Expose internal container port 8000 transparently.
  - Initiate the underlying API executing uvicorn targetting main:app bound fundamentally to 0.0.0.0.

**docker-compose.yml**
- **Responsibility**: Standardises the initiation of the environment efficiently.
- **Implementation specifications**:
  - Define exactly one core backend service titled api.
  - Ensure volume directives map the respective local current directory logically into the container so the statically trained model.pkl guarantees access.
  - Target the respective environment variable loading referencing precisely the hidden .env file location.
  - Bind explicitly external local network port 8000 safely to inner container port 8000.

**.env.example**
- **Responsibility**: Shows configuration requirements without leaking secrets.
- **Implementation specifications**:
  - List exactly GEMINI_API_KEY=your-key-here with no alternative keys present.

**requirements.txt**
- **Responsibility**: Stabilises package targets identically preventing environment drift securely.
- **Implementation specifications**:
  - Include all documented libraries from the tech stack mapping strictly to safely pinned module versions ensuring 100% reproducibility.

**README.md**
- **Responsibility**: Guides developers and acts identically as the project landing page.
- **Implementation specifications**:
  - Supply a clean overarching title alongside exactly one summary paragraph delineating the core context.
  - Present a Prerequisites sector explicitly listing Python 3.11, Docker, and the requisite Gemini API key.
  - Offer sequential Setup Instructions organized comprehensively in clean, numbered format.
  - Explain systematically exactly how to commence the overall demo correctly.
  - Provide an isolated Tech Stack section designed deliberately strictly as informational reading for the recruiting reviewer.
  - Provide a dedicated ML Model block outlining explicitly how the XGBoost methodology operates securely.

## 5. ENVIRONMENT VARIABLES
- **GEMINI_API_KEY**: Required securely by the google-generativeai SDK at runtime to authenticate LLM interaction and generating context embeddings.

## 6. BUILD ORDER
Follow this strict operational progression precisely:
1. Ensure the core directory block structural roots alongside the empty README.md file logically first.
2. Develop the data layer and data generation logic precisely contained within train.py.
3. Explicitly execute train.py immediately yielding the necessary model.pkl securely right away.
4. Expand the static frontend boundary mapping explicitly index.html, style.css, and app.js thoroughly.
5. Create the internal core processors building file_processor.py alongside the isolated rag.py setup securely.
6. Design tools.py correctly intercepting the previously designed components efficiently.
7. Merge operations creating agent.py enforcing the sequential logic cleanly.
8. Unify the stack comprehensively building main.py defining route mappings cleanly.
9. Construct target execution containers building Dockerfile recursively with docker-compose.yml accurately.

## 7. DEMO SCRIPT
Execute the following commands systematically during the demonstration meeting:
- **Step 1**: Execute `python train.py` from the terminal — smoothly explaining the generation of synthetic data to the audience whilst directing their focus to the accuracy metrics and the structural classification logs.
- **Step 2**: Execute `docker-compose up --build` — guiding the recruiter physically through the terminal outputs highlighting the FastAPI backend instantiating reliably on port 8000.
- **Step 3**: Launch the Google Chrome browser targeting precisely `http://localhost:8000` — guiding attention instantly smoothly reflecting the stark dark aesthetic dashboard layout.
- **Step 4**: Physically drag the sample_novacast.txt local file cleanly from the exact operational directory immediately upon the glowing UI upload region.
- **Step 5**: Initiate execution actively clicking the "Run Analysis" visual button — guiding audience focus towards the visible animated spinner, mentioning the LLM RAG actions transpiring safely beneath the DOM.
- **Step 6**: Execute an active visual walkthrough across the fully populated layout sequentially, demonstrating score transitions alongside parsed metrics exactly representing text context. Describe each returned parameter securely. Ensure total operational demo runtime remains under a stringent 5-minute absolute threshold limit.

## 8. POTENTIAL ISSUES AND SOLUTIONS
Provide safeguards resolving specific operational risks:
- PyMuPDF rendering bugs generally require identical base system architecture natively. Resolve by adding dependencies `libmupdf-dev` or equivalents statically within Dockerfile installation rules accurately.
- FAISS installation discrepancies across Linux servers versus Apple architecture natively. Resolve by strictly indicating `faiss-cpu` tightly pinned within requirements instead of generic distributions.
- Execution halts indicating model.pkl not found locally fundamentally due to docker deployment sequentially omitting native data staging. Resolve by instructing users specifically to execute train.py manually prior to initiating complete docker bounds.
- Generation runtime crashes caused strictly by Google embedding API limits native to standard free tier configurations. Resolve by chunking payloads systematically or enforcing a documented brief delay internally per active RAG retrieval block natively.
- Startup API crashes related exclusively to the FastAPI layer intercepting FormData unexpectedly. Resolve primarily validating explicit pinning of `python-multipart` universally inside environment requirements.
- Missing HTTP responses resulting in CORS blocking locally. Resolve securely by implementing explicitly valid CORS middlewares mapped logically locally via main.py securely allowing designated originating ports.