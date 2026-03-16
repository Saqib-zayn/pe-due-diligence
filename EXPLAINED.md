# PE Due Diligence AI — Interview Preparation Guide

---

## 1. HIGH LEVEL OVERVIEW

### For a non-technical recruiter

This project is an AI-powered research assistant built specifically for private equity investors. Instead of spending hours reading through dense financial documents, an analyst can simply drag and drop a company's investment memo or prospectus onto the web page. Within seconds, the system reads the document, extracts all the key financial numbers, identifies the top business risks, and produces a structured investment report — including a numerical score out of 100 that tells the analyst whether the opportunity is a Pass, worth Considering, or a Strong Buy. The interface looks and feels like a professional finance tool: dark, clean, and fast.

### For a technical interviewer

This is a full-stack Python application that combines a Retrieval-Augmented Generation pipeline, a Gemini 2.5 Flash LLM, and a trained XGBoost classifier to automate structured due diligence report generation from raw document uploads. The backend is a FastAPI ASGI server that accepts multipart file uploads (PDF, DOCX, or TXT), extracts plain text via PyMuPDF or python-docx, chunks and embeds that text using Google's embedding model into a FAISS in-memory vector index, and then runs three sequential LLM-powered tool calls — financial metric extraction, risk analysis, and a final synthesis prompt — before feeding the extracted metrics into a pre-trained XGBoost classifier that outputs a confidence-weighted investment score mapped to a 0–100 scale. The frontend is a vanilla JS single-page application served by the same FastAPI process via Jinja2 templating and static file mounting.

### The end-to-end flow

1. The user opens the browser at localhost:8000. FastAPI serves the HTML page through the Jinja2 template engine.

2. The user drags one or more files onto the drop zone. JavaScript intercepts the browser's native drag events, adds the files to an in-memory array, and renders them as removable list items in the UI.

3. The user clicks "Run Analysis". JavaScript bundles the files into a FormData object and sends a POST request to the /analyse endpoint.

4. FastAPI receives the multipart upload. It iterates over each file, passes the raw bytes and filename to the FileProcessor, which detects the file type by extension and extracts plain text using the appropriate library (PyMuPDF for PDFs, python-docx for Word documents, or UTF-8 decoding for text files).

5. The extracted texts are handed to the AgentOrchestrator. The orchestrator creates a RAGPipeline instance and ingests all texts into it. Ingestion means: splitting each document into 500-character chunks with 50-character overlaps, calling the Google embedding API for each chunk to get a numeric vector, and storing those vectors in a FAISS index in RAM.

6. The orchestrator then queries the RAG index three times with different natural-language queries to pull the most relevant chunks for financial data, risk data, and general company context.

7. The financial chunks are sent to Gemini with a structured prompt asking it to extract six specific metrics as a JSON object. The risk chunks go to a separate Gemini call asking for the top five risks as a JSON array.

8. The extracted financial metrics are passed to the pre-trained XGBoost model (loaded from model.pkl), which classifies the company as Pass, Consider, or Strong Buy, and the confidence probability is mapped to a score out of 100.

9. Everything — metrics, risks, score, label, and supporting context — is bundled into one final Gemini prompt that produces a company summary paragraph and a recommendation paragraph.

10. The orchestrator returns a Python dictionary. FastAPI serialises it as JSON and sends it back to the browser.

11. JavaScript receives the JSON, populates every DOM element in the results panel (score number, animated progress bar, label with colour coding, summary text, metrics grid, risks list, recommendation), and smoothly scrolls the panel into view.

---

## 2. THE TECH STACK AND WHY

**FastAPI + uvicorn**
FastAPI is the web framework that runs the backend. It handles routing, receives the file uploads, enforces the response schema with Pydantic, and also serves the frontend HTML and static files — so there is no need for a separate web server. Uvicorn is the ASGI server that actually runs FastAPI. It was chosen over Flask because it is async-native, which matters for a long-running AI pipeline where you do not want the process to block while waiting for LLM responses.

**Gemini 2.5 Flash via google-generativeai SDK**
Gemini is the large language model doing all the language understanding. It is used three times per request: once to extract structured financial metrics, once to identify business risks, and once to write the final company summary and recommendation. Gemini Flash was chosen because it is fast and cost-efficient compared to larger models, which is critical for a demo where response latency matters. The google-generativeai Python SDK handles authentication and the API calls.

**Google Embedding Model (models/gemini-embedding-001)**
Before you can do semantic search over a document, you need to convert each piece of text into a numeric vector that captures its meaning. This is what the embedding model does. It is used during both ingestion (to embed every document chunk) and retrieval (to embed the search query). Using the same model family as the LLM ensures the embedding space is consistent and high quality.

**FAISS (faiss-cpu)**
FAISS is a library from Meta that stores and searches through large collections of numeric vectors extremely quickly. In this project it acts as the vector database — it holds the embeddings of every document chunk in memory and can find the closest matches to a query vector in milliseconds. The cpu-only version is used because this project does not require GPU infrastructure, keeping deployment simple and portable.

**XGBoost + scikit-learn**
XGBoost is a gradient boosting classifier. In this project it was trained on a synthetic dataset of 500 fictional companies and learned to predict whether a company is a Pass, Consider, or Strong Buy based on six financial metrics. Scikit-learn provides the train/test split and the evaluation metrics (accuracy, classification report). XGBoost was chosen because it handles tabular numeric data extremely well, trains fast, is interpretable, and is a standard in quantitative finance contexts. It adds a deterministic, rule-based scoring layer on top of the probabilistic LLM output — which is important for credibility in a finance context.

**joblib**
Joblib serialises the trained XGBoost model to a file called model.pkl and deserialises it at inference time. It is the standard way to persist scikit-learn-compatible models to disk.

**PyMuPDF (fitz)**
PyMuPDF extracts text from uploaded PDF files. It opens the raw bytes directly (no temp file needed), iterates through each page, and pulls all text blocks. It was chosen over alternatives like pdfminer because it is faster, handles a wider range of PDF layouts, and works well from byte streams.

**python-docx**
python-docx reads Word documents (.docx). It parses the document's paragraph structure and concatenates all paragraph text. DOCX files are actually ZIP archives containing XML, and python-docx handles all of that complexity transparently.

**Pydantic**
Pydantic defines the DueDiligenceReport schema — the exact shape of the JSON the /analyse endpoint returns. FastAPI uses this to validate the outgoing response. If the orchestrator accidentally returns a field with the wrong type, Pydantic will catch it before it reaches the client. It is used purely for schema enforcement and serialisation safety.

**Jinja2**
Jinja2 renders the index.html template. In this project it is minimal — the template has no dynamic variables from the server, so Jinja2 is really just used as the mechanism FastAPI requires to serve HTML files. If the project grew, it could be used to inject server-side data into the initial page load.

**python-multipart**
FastAPI requires this library to parse multipart form data, which is the format browsers use when uploading files. Without it, the /analyse endpoint would throw a startup error. It is a hidden dependency that must be explicitly pinned.

**pandas + numpy**
Used in train.py to generate the synthetic training dataset. Numpy provides the random number generation for realistic distributions, and pandas provides the DataFrame structure that XGBoost and scikit-learn expect as input.

**python-dotenv**
Loads the GEMINI_API_KEY from a .env file into the process environment at startup. This keeps secrets out of the codebase and allows the same code to run in development (reading from .env) and in Docker (reading from environment variables set by docker-compose).

**Docker + docker-compose**
Docker packages the entire application — Python runtime, system dependencies, application code, model file — into a single reproducible image. docker-compose defines how to run that image: which ports to expose, which environment file to load, and how to mount the local directory so model.pkl is accessible inside the container.

**Vanilla JavaScript (no framework)**
The frontend deliberately uses no framework — no React, no Vue. This was a deliberate choice to keep the demo dependency-free and fast loading. The entire interactivity (drag-and-drop, fetch, DOM updates, animations) is handled in about 220 lines of well-organised vanilla JS.

---

## 3. FILE BY FILE BREAKDOWN

---

### main.py

**Single job:** Entry point. Wires together the web framework, routes, middleware, file serving, and the AI pipeline.

**Walkthrough:**

The file starts by importing FastAPI, its supporting classes, and the two internal modules it delegates work to: FileProcessor and AgentOrchestrator.

It creates the FastAPI application instance, then immediately adds CORS middleware configured to allow all origins. This is intentional for a local demo — in production you would restrict this to your frontend's domain.

It mounts the /static folder so that style.css and app.js are served directly by FastAPI without any extra configuration. It also sets up Jinja2 to look in the /templates folder for HTML files.

The DueDiligenceReport class is a Pydantic BaseModel that defines exactly what the JSON response from /analyse must look like: seven fields with their types. FastAPI uses this as the response_model to validate and serialise the output.

There are three routes:
- GET / returns the HTML dashboard by rendering index.html through Jinja2.
- GET /health returns a simple JSON object. This is a standard pattern for load balancers and health checks to confirm the service is alive.
- POST /analyse is the core route. It accepts a list of UploadFile objects (the uploaded documents), reads the bytes from each file, passes them to FileProcessor, and if any file type is unsupported it catches the ValueError and returns an HTTP 400 error with a clear message. All successfully extracted texts are handed to AgentOrchestrator, and the resulting dictionary is returned as a JSONResponse.

**What goes in:** HTTP requests from the browser. **What comes out:** HTML, JSON, or HTTP error responses.

**How it connects:** Imports and instantiates FileProcessor and AgentOrchestrator on every request (stateless design). It is the only file the uvicorn server is told to run.

**Interesting detail:** The response_model=DueDiligenceReport annotation on /analyse means FastAPI will validate the dictionary returned by the orchestrator against the schema before sending it to the client — a useful safety net when the LLM might produce unexpected output shapes.

**Interview answer:** "main.py is the composition root. It does not contain any business logic — it just wires together the web layer, the file processing layer, and the AI layer. I kept it intentionally thin so that any component can be swapped out independently."

---

### file_processor.py

**Single job:** Convert any uploaded file — regardless of format — into a plain text string.

**Walkthrough:**

The FileProcessor class has one public method called process. It takes a filename and raw bytes. It looks at the file extension by converting the filename to lowercase and checking which extension it ends with. Depending on the extension, it routes the bytes to one of three private methods.

extract_from_pdf imports PyMuPDF (as fitz), opens a document directly from the byte stream (no temp file written to disk), iterates through every page, calls get_text("text") on each page, and joins the results with newlines.

extract_from_docx wraps the bytes in a BytesIO stream (so python-docx can read it as if it were a file), opens a Document, and joins all paragraph text with newlines.

extract_from_txt simply decodes the bytes as UTF-8.

If the extension is not in the supported set, it raises a ValueError with a descriptive message that names the unsupported extension and lists what is accepted. This ValueError is caught upstream in main.py and converted to an HTTP 400 error.

**What goes in:** A filename string and raw file bytes. **What comes out:** A plain text string.

**How it connects:** Called by main.py before anything else. Its output feeds into AgentOrchestrator.

**Interesting detail:** PyMuPDF is imported inside the method rather than at the top of the file. This is a lazy import — it delays the import until the method is actually called. This means if you are only uploading text files, the PDF library never gets loaded.

**Interview answer:** "file_processor.py is a pure transformation layer with no knowledge of AI or the web. It uses the single responsibility principle — one class, one job. I made it raise a ValueError for unsupported types rather than returning an empty string, so the error propagates clearly up to the user rather than silently producing a bad report."

---

### rag.py

**Single job:** Store document content as searchable vectors and retrieve the most relevant chunks for a given query.

**Walkthrough:**

The RAGPipeline class maintains two pieces of state: a list of raw text chunks, and a FAISS index that stores their corresponding embedding vectors.

_split_into_chunks takes a long text string and slices it into pieces of 500 characters. After each chunk it advances the start position by 450 characters (500 minus the 50-character overlap). The overlap ensures that a sentence split across a chunk boundary still appears in at least one complete chunk.

_embed_text calls the Google embedding API with a task_type of "retrieval_document", which tells the model to optimise the embedding for being stored and searched, as opposed to being used as a query.

ingest calls these two helpers together. For each chunk it gets an embedding, waits 0.5 seconds (to avoid hitting the free-tier rate limit on the embedding API), then converts all embeddings to a float32 numpy array. If no FAISS index exists yet, it creates one using IndexFlatL2 — a flat index that does exhaustive Euclidean distance search. It then adds all vectors to the index and appends the raw chunk strings to the list. Crucially, calling ingest multiple times accumulates into the same index, so multiple uploaded files all share one searchable space.

retrieve takes a plain English query, embeds it with task_type "retrieval_query", converts it to a 1xN numpy array, and calls index.search to find the closest K vectors. It uses min(top_k, index.ntotal) to avoid asking for more results than there are chunks. It returns the raw text strings corresponding to the found indices.

**What goes in:** Plain text strings (ingest) or a query string (retrieve). **What comes out:** A list of the most semantically relevant text chunks.

**How it connects:** Created and called by AgentOrchestrator. Has no knowledge of the LLM or the file processor.

**Interesting detail:** The task_type distinction between "retrieval_document" and "retrieval_query" is a meaningful API parameter. Google's embedding model produces different vector representations depending on whether you are encoding something to be stored versus something to be searched. Using the wrong type would degrade retrieval quality.

**Interview answer:** "rag.py implements a minimal but complete RAG pipeline. I chose IndexFlatL2 because with a few hundred chunks from a small document set, exhaustive search is fast enough and removes the approximation error you get with ANN indexes like HNSW. The 50-character chunk overlap is a deliberate design choice to prevent important context from falling between chunk boundaries."

---

### tools.py

**Single job:** Provide the three discrete analytical functions the agent uses as tools — metric extraction, risk analysis, and investment scoring.

**Walkthrough:**

extract_financial_metrics takes a list of text chunks and a Gemini model instance. It joins the chunks with separator strings, inserts them into a prompt that instructs the LLM to return exactly six financial fields as a JSON object, calls the model, and then parses the response. The parsing is defensive: it first strips any markdown code fences the model might accidentally include, tries json.loads, and if that fails uses a regex to find any JSON-shaped substring. After parsing, it uses setdefault to ensure all six keys are always present — even if the model returned null for some of them.

analyse_risks works the same way but with a different prompt asking for exactly five risks as a JSON array. It pads the list to exactly five items if the model returns fewer, ensuring the frontend always has five things to render.

predict_investment_score is entirely different — it does not call the LLM at all. It loads the trained XGBoost model from model.pkl using joblib, substitutes sensible defaults for any metric fields that came back as null, builds a pandas DataFrame with the features in the exact order the model was trained on, runs predict to get the class label (0, 1, or 2), and runs predict_proba to get the confidence probability for that class. The final score is calculated by mapping the confidence into a band: class 0 maps to 5–35, class 1 to 40–65, class 2 to 70–100. A confidence of 1.0 would give the maximum of the band, a confidence near 0.5 would give the minimum.

**What goes in:** Text chunks + model instance (tools 1 and 2); a metrics dictionary (tool 3). **What comes out:** A dict of metrics, a list of risk strings, or a (score, label) tuple.

**How it connects:** Called exclusively by AgentOrchestrator in sequence. The output of tool 1 feeds directly into tool 3.

**Interesting detail:** The score formula — low + (high - low) * confidence — is a clever way to make the score feel meaningful. A company that the model is barely confident is a "Consider" gets a score around 40, while a company the model is very confident about gets closer to 65. This avoids the trap of all "Consider" companies returning the same number.

**Interview answer:** "I separated the tools from the agent intentionally so each function is testable in isolation. The investment scoring deliberately does not call the LLM — the ML model provides a deterministic, auditable score based on hard numbers, which adds a layer of rigour that pure LLM output cannot. If the LLM hallucinates a metric, the defaults ensure the model still runs rather than crashing."

---

### agent.py

**Single job:** Orchestrate the full analytical pipeline in sequence and assemble the final report.

**Walkthrough:**

AgentOrchestrator's constructor reads the GEMINI_API_KEY from the environment, configures the google-generativeai SDK, and instantiates a GenerativeModel pointing at "gemini-2.5-flash".

The run method takes a dictionary mapping filenames to extracted text strings. It proceeds through five steps:

Step 1: Creates a RAGPipeline and ingests every document's text into it.

Step 2: Queries the RAG index with a string listing financial terms ("revenue growth EBITDA margin debt equity market size founding year team size") to pull the five chunks most likely to contain financial data. Passes those chunks to extract_financial_metrics.

Step 3: Queries the RAG index with risk-related terms to pull the five most relevant chunks. Passes those to analyse_risks.

Step 4: Passes the extracted metrics dictionary to predict_investment_score. The ML model returns a score and a label.

Step 5: Queries the RAG index one more time for general company context, then builds a detailed prompt that includes all the outputs from steps 2–4 plus the raw context. It sends this to Gemini and asks it to return a JSON object with "company_summary" and "recommendation" keys only. The response goes through the same defensive JSON parsing pattern as the tools.

Finally it assembles and returns the complete report dictionary containing all seven fields.

**What goes in:** A dict of {filename: text}. **What comes out:** A dict matching the DueDiligenceReport schema.

**How it connects:** Called by main.py. Calls RAGPipeline, extract_financial_metrics, analyse_risks, and predict_investment_score in sequence.

**Interesting detail:** The SUMMARY_PROMPT is defined as a module-level constant rather than inside the method. This is a clean pattern — it keeps the prompt visible and editable without digging through method logic. Also note the agent queries the RAG index three separate times with three different queries, rather than retrieving everything once. This is intentional: each query is tuned to pull the most relevant context for a specific task, rather than getting a generic mix.

**Interview answer:** "agent.py is the orchestration layer. I designed it as a sequential pipeline rather than a tool-calling loop because the steps have a clear dependency order — you need metrics before you can score, and you need the score before you can write the final summary. The RAG queries are specialised per task, which gives each LLM call the most signal-rich context possible."

---

### train.py

**Single job:** Generate a synthetic training dataset, train an XGBoost classifier, evaluate it, and save the model to disk.

**Walkthrough:**

generate_synthetic_dataset creates 500 fictional companies using realistic statistical distributions. Revenue growth is drawn from a normal distribution centred at 12% with a standard deviation of 15 (so it includes negative growth). EBITDA margin is normally distributed around 18%. Debt-to-equity follows an exponential distribution (many companies have low debt, a few have very high debt). Market size is uniformly distributed between 1 and 50 billion. Founding year is a random integer between 1985 and 2022. Team size is between 10 and 1000.

Labels are assigned by a composite rule-based scoring system: a company earns points for having revenue growth above 15%, EBITDA margin above 20%, debt-to-equity below 0.5, market size above 10 billion, and team size above 100. A random 0 or 1 is added as noise. The composite score is then binned with pd.cut into three classes: 0 to 2 is Pass, 3 to 4 is Consider, 5+ is Strong Buy.

train_and_save splits the data 80/20 with stratification, trains an XGBoost classifier with 200 trees, max depth 4, learning rate 0.1, and subsampling of 80% of rows and features per tree. It prints accuracy and a full classification report, then saves the model using joblib.dump.

**What goes in:** Nothing (runs standalone). **What comes out:** model.pkl on disk.

**How it connects:** Must be run once before the Docker container starts. tools.py loads the resulting model.pkl at inference time.

**Interesting detail:** The labels are derived from deterministic business rules (revenue growth above 15% earns 2 points, etc.) rather than being random. This means the XGBoost model is learning to replicate a consistent set of human-defined investment criteria. The small random noise (0 or 1 extra points) prevents the model from perfectly memorising the rules and forces it to learn probabilistic boundaries.

**Interview answer:** "I used synthetic data because there is no public dataset of private equity investment decisions with ground truth labels. The label generation logic encodes real PE investment heuristics — high growth, strong margins, low leverage. XGBoost is a natural fit for this kind of structured tabular data and is widely used in quantitative finance. The stratified train/test split ensures all three classes are proportionally represented in both sets."

---

### static/app.js

**Single job:** Handle all frontend behaviour — drag-and-drop, API calls, and rendering the results into the DOM.

**Walkthrough:**

The entire script is wrapped in an immediately invoked function expression (IIFE) so no variables leak into the global scope.

At the top, it gets references to every DOM element it will need to update, using getElementById. This is done once at startup rather than inside event handlers for efficiency.

selectedFiles is a plain array that stores the File objects the user has added.

The drag-and-drop logic listens to three events on the drop zone: dragover (prevents the browser's default behaviour of navigating to the file and adds a CSS class for the glow effect), dragleave (removes the glow class only when the mouse actually leaves the zone, not when it crosses over child elements — a subtle bug fix using relatedTarget), and drop (calls addFiles with the dropped files).

Clicking the drop zone triggers the hidden file input. The input's change event calls addFiles. The input value is reset after each selection so the same file can be removed and re-added.

addFiles checks for duplicate filenames before pushing to the array, then calls renderFileList which rebuilds the displayed list entirely on each change and disables the Run button if no files are selected.

The run button's click handler builds a FormData object with all selected files appended under the key "files", sends a POST request to /analyse, and handles three states: loading (spinner visible, button disabled), success (calls renderResults), and error (shows the error message div).

renderResults maps every field of the JSON response to its DOM element. It applies CSS colour classes — score-pass, score-consider, or score-buy — based on the label string. The score bar animates from 0 to the final width using a CSS transition triggered 100ms after the elements become visible. It uses escHtml to sanitise all displayed text, preventing XSS in case a filename or LLM response contains HTML characters.

**What goes in:** User interactions (drag, click) and JSON from the API. **What comes out:** DOM mutations that populate the results panel.

**How it connects:** Talks to main.py's /analyse route. Has no dependencies on any backend Python code.

**Interesting detail:** The setTimeout of 100ms before setting the score bar width is a deliberate trick. If you set the width immediately after removing the "hidden" class, the browser may not have completed the layout pass yet, so the transition does not animate. The small delay ensures the element is rendered before the CSS transition begins.

**Interview answer:** "I chose vanilla JavaScript intentionally. The interaction surface is small and well-defined, so adding React or Vue would be over-engineering. The escHtml function prevents XSS — I always sanitise content that comes from external sources before inserting it into the DOM. The IIFE pattern keeps the module self-contained without needing a bundler."

---

### static/style.css

**Single job:** Define the dark finance visual theme and all UI component styles.

**Walkthrough:**

All colours and spacing constants are defined as CSS custom properties on :root. This means every colour used anywhere in the file references a variable like var(--accent) rather than a hardcoded hex value. Changing the theme requires editing one block.

The header uses position: sticky so it stays at the top while the user scrolls, with backdrop-filter: blur for a frosted glass effect. The green "Live" badge pulses using a keyframe animation on its dot.

The drop zone uses a dashed border that transitions to a glowing blue (box-shadow with the accent colour) on hover or when a file is dragged over it. This is controlled by the drag-over CSS class toggled by JavaScript.

The score colouring system uses three sets of classes — score-pass/score-consider/score-buy for the number, label-pass/label-consider/label-buy for the pill, and bar-pass/bar-consider/bar-buy for the progress bar — all sharing the same danger/warning/success colour variables.

The score bar itself starts at width: 0% and uses a 1-second CSS transition to animate to its target width when JavaScript sets it.

The results panel entrance uses a keyframe animation called results-enter that fades in and slides up from 20px below — giving a smooth reveal when analysis completes.

Responsive breakpoints at 768px collapse the two-column top row to a single column, and at 480px the metrics grid goes to a single column.

**Interview answer:** "I used CSS custom properties rather than a preprocessor like SASS because the colour system is simple enough that variables alone are sufficient. The animation approach — CSS transitions and keyframes triggered by JavaScript class changes — keeps animation logic in CSS where it belongs, with JavaScript only responsible for toggling the classes."

---

### templates/index.html

**Single job:** Define the structural skeleton of the single-page application.

**Walkthrough:**

The file loads Inter from Google Fonts and then the project's style.css. It has no inline styles.

The header section contains the brand icon (an SVG polyline that looks like a pulse/chart line), the title, the subtitle, and the animated "Live" badge.

The upload panel contains the drop zone div (which wraps the hidden file input), the file list ul (empty initially, populated by JavaScript), the Run Analysis button (disabled by default), the loading spinner div (hidden by default), and the error message div (hidden by default).

The results section starts hidden. It is structured as: a files-analysed container for the pills, then a two-column row with the score card on the left and the company summary card on the right, then a full-width metrics grid with six metric items each showing an icon, a label, and a value slot, then a risks list, and finally the recommendation card.

Every interactive element has an id attribute that app.js references. Every value slot shows "—" as its initial content.

**Interview answer:** "The HTML is purely structural — no inline styles, no inline scripts. Every element that JavaScript touches has a clear, semantic id. The results panel starts hidden and is revealed by JavaScript removing the hidden class, which triggers the CSS entrance animation. I separated concerns completely: HTML for structure, CSS for style, JavaScript for behaviour."

---

## 4. THE AI AND ML EXPLAINED

### What RAG is and how this project uses it

RAG stands for Retrieval-Augmented Generation. The problem it solves is this: large language models have a limit on how much text you can send them in a single prompt. If a document is 50 pages long, you cannot just paste the whole thing into a prompt and ask questions about it.

RAG solves this by breaking the document into small pieces (chunks), converting each piece into a numeric representation (an embedding), storing those embeddings in a searchable database, and then — when you need to ask the LLM something — first searching the database to find the pieces most likely to contain the answer, and only sending those pieces to the LLM.

In this project, when a user uploads a document, the RAGPipeline splits it into chunks of 500 characters with a 50-character overlap between adjacent chunks. Each chunk is then sent to Google's embedding API which returns a list of numbers (a vector) that represents the meaning of that chunk. These vectors are stored in FAISS.

When the agent needs to extract financial metrics, it does not send the whole document to Gemini. Instead it searches the FAISS index with a query like "revenue growth EBITDA margin debt equity", finds the five chunks whose embeddings are closest to that query's embedding, and sends only those five chunks to Gemini. The LLM gets focused, relevant context rather than noise.

This approach has two benefits: it respects the LLM's context window limits, and it tends to produce better results because the model is not distracted by irrelevant content.

### What a vector database is using FAISS

A vector database is a data store optimised for storing and searching through high-dimensional numeric vectors. Instead of asking "find me the row where name = 'NovaCast'", you ask "find me the vectors that are closest to this query vector."

In this project, FAISS holds a flat index — meaning every vector is stored in a matrix in RAM. When you call index.search with a query vector, FAISS computes the Euclidean distance (L2 distance) between the query vector and every stored vector, and returns the indices of the K smallest distances. These indices correspond to the most semantically similar chunks.

The FAISS index in rag.py is created lazily — it does not exist until the first call to ingest, at which point it learns the dimensionality (the number of numbers per vector, which is determined by the embedding model) and initialises itself. Subsequent ingest calls add more vectors. The parallel list of raw chunk strings (self._chunks) is what allows the system to go from "index 3 is the closest match" back to the actual text of that chunk.

IndexFlatL2 does not approximate — it checks every single vector. For the scale of this project (a few hundred chunks from a handful of documents), this is fast enough and gives perfect recall. At larger scale you would switch to an approximate index like IndexIVFFlat or HNSW.

### What the agent is doing step by step

The AgentOrchestrator is not an LLM agent in the autonomous sense — it does not decide its own next actions. It is a fixed sequential pipeline that orchestrates LLM calls and ML inference in a predetermined order.

Step 1 is ingestion: all uploaded document texts are fed into the RAG pipeline to build the searchable index.

Step 2 is targeted retrieval for financial data: the agent searches for chunks related to financial metrics and sends them to Gemini with a strict extraction prompt. The prompt tells Gemini to return exactly six named fields as JSON and nothing else.

Step 3 is targeted retrieval for risks: same pattern but with risk-oriented search terms and a risk-focused prompt asking for exactly five items.

Step 4 is ML scoring: the extracted metrics are passed to the XGBoost model. This step does not use the LLM at all — it is deterministic inference on structured numbers.

Step 5 is synthesis: the agent pulls one more set of general context chunks from the RAG index and builds a final prompt that includes all previous outputs (metrics, risks, score, label, and raw context). It asks Gemini to write a professional company summary and a clear investment recommendation. The prompt explicitly asks for JSON with exactly two keys, which makes parsing reliable.

### The ML model — what it is, what it predicts, and what it adds

The XGBoost model was trained using train.py on a synthetic dataset of 500 fictional companies. Each company was represented by six financial metrics: revenue growth percentage, EBITDA margin, debt-to-equity ratio, market size in billions, founding year, and team size.

Labels (0=Pass, 1=Consider, 2=Strong Buy) were assigned by a rule-based scoring function that encoded real PE investment criteria: high growth and margins earn points, low leverage earns points, large markets earn points. This means the model learned to replicate professional investment screening logic from structured data.

At inference time, the model takes the six metrics extracted from the uploaded document, predicts which class the company falls into, and also outputs the probability of that prediction. The probability is used to produce a continuous score out of 100: a high-confidence "Strong Buy" gets a score in the 85–100 range, a barely-confident "Strong Buy" gets something around 70.

What the ML model adds to the project is a structured, auditable, deterministic signal that is independent of the LLM's language generation. The LLM might produce different wording on every run; the ML score for the same six numbers will always be the same. In a finance context, this kind of reproducibility is important for credibility.

### Embeddings in plain English using this codebase

An embedding is a way of turning a piece of text into a list of numbers such that texts with similar meanings produce similar lists of numbers. The meaning of "similar" here is geometric: similar texts produce vectors that are close together in high-dimensional space.

In rag.py, when a chunk of text like "NovaCast reported revenue growth of 18.4% and an EBITDA margin of 21%" is sent to the embedding API, it comes back as a list of roughly 768 numbers. A different chunk about EBITDA and revenue would produce a similar list. A chunk about supply chain risks would produce a very different list.

When the agent queries the RAG index for financial data, it embeds the query string "revenue growth EBITDA margin debt equity market size founding year team size" into its own vector. FAISS then finds which stored chunk vectors are geometrically closest to this query vector. Because embeddings capture meaning rather than just words, a chunk that talks about "earnings before interest and taxes" would still be retrieved even if the query said "EBITDA", because the embedding model knows these concepts are related.

The key detail in rag.py is the task_type parameter. Chunks are embedded with task_type "retrieval_document" and queries with task_type "retrieval_query". This is because the optimal representation for something you are storing is slightly different from the optimal representation for something you are searching with. Using the correct task type improves retrieval accuracy.

---

## 5. INTERVIEW QUESTIONS AND ANSWERS

**Q1: Walk me through what happens when I drop a file into your application.**

The browser fires a drop event that JavaScript intercepts. The file is added to an in-memory array and rendered in the UI. When I click Run Analysis, the file is bundled into a FormData object and sent via fetch to POST /analyse. FastAPI receives the multipart upload, reads the raw bytes, and passes them to FileProcessor, which detects the extension and uses the appropriate library — PyMuPDF for PDFs, python-docx for Word files, plain UTF-8 decoding for text files — to extract plain text. That text goes to AgentOrchestrator, which ingests it into a FAISS vector index, runs three targeted RAG retrievals, calls Gemini twice for structured extraction and once for synthesis, runs the XGBoost model for scoring, assembles a report dictionary, and returns it as JSON. JavaScript receives the JSON and populates every card in the results panel.

**Q2: Why did you use RAG instead of just pasting the whole document into the prompt?**

Two reasons. First, practical: LLMs have context window limits, and investment memos can be long. If the document exceeds the context window, you either truncate it (losing information) or RAG it (keeping all of it searchable). Second, quality: sending a focused 2,000-character excerpt that is directly relevant to your question tends to produce better, more precise LLM outputs than burying the relevant information in 50 pages of text. The model has less noise to work through.

**Q3: Why XGBoost instead of asking the LLM to produce the investment score?**

Determinism and credibility. If you ask Gemini to score a company out of 100, you will get different numbers on different runs, and it is impossible to explain exactly why it gave that score. XGBoost, trained on explicit criteria (revenue growth above 15%, debt-to-equity below 0.5, etc.), will always give the same score for the same inputs, and you can inspect the model's feature importances to understand which metrics it weighted most heavily. In a finance context, auditability matters — an investment committee needs to be able to trace exactly why a score was produced.

**Q4: What are the limitations of training on synthetic data?**

The model learns to replicate the rules I used to generate the labels, not actual historical investment outcomes. If my rule-based scoring missed an important factor (say, geographic concentration risk), the model would never learn to penalise for it. In a real deployment you would want to train on historical deal data with actual returns, but that data is private and scarce. The synthetic approach is a reasonable proxy for a demo — it shows the ML architecture works — but the model should not be used for real investment decisions without proper validation against ground truth.

**Q5: How does FAISS find the most relevant chunks?**

FAISS stores all chunk embeddings as rows in a float32 matrix. When you search, it takes the query embedding vector and computes the Euclidean (L2) distance between it and every stored vector. The chunks with the smallest distances are the most similar. This is a brute-force search — IndexFlatL2 checks every vector. For this project's scale that is fine, but at tens of millions of chunks you would switch to an approximate nearest neighbour index that trades a small amount of recall for a large reduction in search time.

**Q6: What would break if someone uploaded a 500-page PDF?**

Two things. First, chunking a 500-page PDF would produce hundreds or thousands of chunks, each requiring a separate embedding API call with a 0.5-second delay between them. The request would take many minutes to complete. Second, depending on the Google embedding API tier, you might hit rate limits before finishing. The fix would be to batch embedding calls and increase rate limit thresholds, or to use asynchronous embedding with proper retry logic.

**Q7: Why does the /analyse endpoint create a new FileProcessor and AgentOrchestrator on every request?**

Because they are stateless tools for that request's lifecycle. FileProcessor has no state at all. AgentOrchestrator creates a new RAGPipeline per request, which means each analysis starts with a fresh FAISS index containing only the uploaded documents — no contamination from a previous user's upload. If these were singletons, a user uploading Company A's documents might get Company B's chunks in their results if another request was processed concurrently.

**Q8: How do you prevent the LLM from returning invalid JSON?**

Defensively. The prompt instructs the model to return only a JSON object with no markdown and no explanation. After receiving the response, the code strips any markdown code fences using a regex. It then tries json.loads. If that fails, it uses a second regex to find any substring that looks like a JSON object (starting with { and ending with }) and tries to parse that. If even that fails, it falls back to an empty dict or list. The result then has setdefault called on all required keys, so missing fields are set to null rather than causing a KeyError downstream.

**Q9: How would you scale this to handle 50 concurrent users?**

Several changes. First, move from a single uvicorn process to multiple workers (uvicorn --workers 4) or deploy behind a process manager like Gunicorn. Second, replace the in-memory FAISS index with a persistent vector store like Pinecone or Weaviate so the index survives restarts and can be shared. Third, make the LLM calls asynchronous rather than synchronous so one slow API call does not block others. Fourth, add a task queue (Celery with Redis) so long-running analyses happen in background workers rather than blocking the HTTP response.

**Q10: Why is python-multipart listed as a separate dependency when FastAPI is already in the requirements?**

FastAPI does not bundle it as a hard dependency because not every FastAPI application needs multipart support. If you use File or UploadFile in a route and python-multipart is not installed, FastAPI will raise a RuntimeError at startup. Pinning it explicitly in requirements.txt prevents this from being discovered at runtime rather than at install time.

**Q11: What is the purpose of the 50-character chunk overlap in RAG?**

When you split text at fixed character boundaries, a sentence or piece of information might be cut in half. The overlap ensures that any 50-character window of text appears in at least two adjacent chunks. This way, if the most important sentence in a document happens to straddle a chunk boundary, at least one of the two chunks will contain it in a usable form. Without overlap, retrieval would have a systematic blind spot at every chunk boundary.

**Q12: How does the investment score out of 100 get calculated?**

The XGBoost model returns two things: a predicted class (0, 1, or 2) and the probability of that prediction. Each class maps to a score band — Pass maps to 5–35, Consider to 40–65, Strong Buy to 70–100. The final score is the lower bound of the band plus the confidence probability multiplied by the band width. So a company predicted as "Consider" with 80% confidence gets a score of roughly 40 + (0.80 × 25) = 60. This ensures the score reflects both the category and the strength of the prediction.

**Q13: What PE-specific domain knowledge is embedded in this project?**

The six financial metrics chosen — revenue growth, EBITDA margin, debt-to-equity, market size, founding year, team size — are standard PE screening criteria. The label generation logic in train.py encodes PE heuristics: growth above 15% is a strong positive signal (weighted 2×), margins above 20% are equally important (weighted 2×), low leverage is a good sign (1×), large addressable markets are attractive (1×). The EBITDA margin is the key profitability measure PE firms use rather than net income, because it strips out financing and accounting effects. The framing of the risk analysis as "top 5 business risks" and the recommendation as "Pass, Consider, or Strong Buy" mirror real investment committee vocabulary.

**Q14: If a recruiter asked why you built this specifically — what was the decision?**

The intersection of AI and finance is exactly where the most interesting engineering problems are right now. Unstructured document analysis is a genuine pain point in PE — analysts spend significant time reading and summarising memos. Building a system that combines LLM reasoning for the qualitative layer with ML classification for the quantitative layer demonstrates that you understand the difference between when to use each approach. The RAG architecture specifically shows awareness of the practical constraints of LLMs in enterprise settings — you cannot just paste documents into a prompt and call it a system.

**Q15: What is one thing you would do differently if this were a production system?**

I would not use a synchronous, blocking HTTP response for a pipeline that can take 30–60 seconds. Instead, the /analyse endpoint would immediately return a task ID, and the client would poll a /status/{task_id} endpoint until the job completes. This is a much better user experience — the browser does not hang — and it allows the backend to handle concurrent requests properly. The current design works fine for a demo where one person runs one analysis at a time, but it would fall apart under real load.

---

## 6. WHAT YOU WOULD CHANGE OR IMPROVE

**1. If I had more time, I would replace the synchronous request–response pattern with an async task queue.**

Right now, clicking "Run Analysis" keeps the browser waiting for the full pipeline to complete — which includes multiple embedding API calls with rate-limit delays, two LLM inference calls, and ML model loading. This can take 30 seconds or more. A production implementation would have the /analyse endpoint submit the job to a Celery task queue backed by Redis, return a job ID immediately, and have the frontend poll a /status/{id} endpoint. This would also allow the backend to handle multiple concurrent requests without blocking.

**2. If I had more time, I would train the ML model on real historical data.**

The XGBoost model was trained on 500 synthetic companies where the labels were generated by rules I defined. This means the model learned to replicate my rules, not actual investment outcomes. In a real system you would want historical deal data — companies that were evaluated, the decisions made, and the eventual returns — to train a model that has predictive validity. Even a small dataset of 200 real deals with labelled outcomes would be more credible than synthetic data.

**3. If I had more time, I would add persistent document storage and a session system.**

Currently every request starts fresh. If a user uploads a document, analyses it, and comes back an hour later to run a follow-up query, they have to upload the same document again and wait for it to be re-ingested. A proper implementation would store uploaded documents and their FAISS indexes persistently (in something like S3 for the documents and Pinecone or Weaviate for the vectors), keyed to a session or user ID. This would also enable the interesting use case of comparing multiple companies against each other.

**4. If I had more time, I would add structured logging and tracing throughout the pipeline.**

Right now, if a request fails halfway through — say the embedding API rate-limits on chunk 12 — there is no visibility into where it failed or what the intermediate outputs were. A production system would log each pipeline step with timing, output size, and any errors, and would emit structured traces (using something like OpenTelemetry) that allow you to see the full execution path for any request. This is especially important for an AI system where debugging requires understanding what context was retrieved and what the model was given.

**5. If I had more time, I would add confidence indicators and source citations to the report.**

The current output tells you the financial metrics but does not tell you how confident the system is that those numbers are correct, or which specific sentences in the document they came from. A more trustworthy system would highlight the exact excerpt that each metric was extracted from, flag cases where the LLM returned null (meaning it could not find the number), and give the analyst a way to verify the AI's extraction against the source. In a finance context, traceability from conclusion back to evidence is not optional — it is a compliance requirement.
