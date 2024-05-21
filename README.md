# About

This project is a RAG app that is capable of uploading a document to be stored, creating embeddings from the document content and querying the contents of the document with natural language.

## Built with

[FastAPI](https://fastapi.tiangolo.com/)

[Minio](https://min.io/)

[OpenAI (chat and embedding models)](https://openai.com/api/)

[Pinecone](https://www.pinecone.io/)

# Getting started

This section outlines the setup and running examples from Postman.

## Setup

1. Have Docker installed and running.
    - Instructions can be found [here](https://docs.docker.com/engine/install/).

2. Set environment variables in file `./etc/.env`.
    - Most env vars are already set to reasonable values. The only ones which you **must** set with real values are the *OPEN_API_KEY* and *PINECONE_API_KEY*.

3. Run the `run_app.sh` script from the project root dir and you're all set to send requests to the API.
    - `. ./run_app.sh`

## Running Postman example requests

To run example requests, there is a Postman collection (v2.1) under `./etc/postman/sample_requests.json`. With the Postman desktop client downloaded, you may [import the collection](https://docs.tink.com/entries/articles/postman-collection-for-account-check) and use them as template requests to send to the app.

Please note that there are 2 copies for each request for each endpoint in the collection. One is for the provided Japanese sample files and the other is for an example in English. Before running any of the requests, please make sure that the `x-api-key` header is properly set (i.e. matching the `API_KEY` set in the `./etc/.env` file).

### Upload example request

`upload - docker - english` example request

- Select files to upload under `Body -> form-data`.

![Request example](./etc/readme_images/upload_request.png)

- You should receive a list of signed URLs in the response:

```
{
    "signed_urls": [
        "http://minio1:9000/denis-test/experiential_colearning.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=user%2F20240521%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20240521T043714Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=69a5dde59f3a356d43482ff875d5f0e2dae69597d12638fb8f740ffe2ca69a9e"
    ],
    "details": "All files successfully uploaded."
}
```

### Create embeddings example request

`create_embeddings - docker -english` example request

- Use a signed URL returned from the upload request as the key to the `url` field in the `Body` of the request.

![alt text](./etc/readme_images/create_embeddings_request.png)

- You should receive a list of hashs corresponding to the id of each embedded chunk of the document stored in the vector store.

```
{
    "ids": [
        "55c8bb0bb1eda4631f1e4b6715a95f6f82c528a931d97257b51abf3a6ebc5514",
        "f719f7e9e0b1311a0a7d531c6cde2758efe3caccc5bf2c403115fc755cadd8a8",
        ...
    ],
    "timestamp": 1716266274002477,
    "file_name": "experiential_colearning.txt",
    "details": "Sucessfully added document to vector store under index 'denis' with namespace 'test'"
}
```

### Query example request

`query - docker - english` example request

- Send the request with a question as the value to the `query` key field in the `Body` of the request.

![alt text](./etc/readme_images/query_request.png)

- You should receive a natural language response in English along with the context chunks used to generate the answer.

```
{
    "answer": "- **Definition**: Experiential Co-Learning is a novel multi-agent learning paradigm designed to enhance the interactive task-solving abilities of software-developing agents by leveraging accumulated experiences.\n  \n- **Key Components**:\n  1. **Co-Tracking Module**:\n     - Establishes a rehearsal collaboration between an instructor and an assistant.\n     - Tracks \"historical trajectories\" for various training tasks, capturing the detailed progression and strategies employed.\n  \n  2. **Co-Memorizing Module**:\n     - Extracts \"shortcuts\" from procedural trajectories based on external feedback.\n     - Integrates these shortcuts into the agents' collective experience pools to enhance future task-solving efficiency.\n  \n  3. **Co-Reasoning Module**:\n     - Utilizes the collective experience pools to improve the interaction of instructions and responses.\n     - Enhances the agents' ability to collaboratively solve unseen tasks.\n\n- **Benefits**:\n  - **Efficiency**: Reduces repetitive errors and unnecessary trial-and-error processes.\n  - **Autonomy**: Minimizes the need for human involvement by enabling agents to learn from past experiences.\n  - **Collaboration**: Facilitates a more effective and cohesive approach to task completion through mutual reasoning and experience sharing.\n\n- **Application**: Particularly useful in complex scenarios like software development, where tasks require a blend of natural and programming language skills and continuous alterations.",
    "context": [
        "Experiential Co-Learning of Software-Developing Agents ...",
        "autonomy that surpasses the traditional prompt- ..."
    ]
}
```

## For developers

You may opt to interact with the API endpoints uniquely through a local Docker deployment for simplicity and ease of use. Alternatively, if you want to iterate on the API without having to rebuild the Docker container each change, you may run app (including the Minio client) with `run_app.sh` script in one terminal and run the Fast API app in another terminal with `unvicorn` directly. To do so:

1. Install Poetry

> pip install poetry

2. Install dependencies

> poetry install

3. Run API with uvicorn

> uvicorn --reload src.app:app --host 0.0.0.0 --port 8000

# Database

## Vector store

This RAG app uses `Pinecone` as a vector store to store and save chunked embedded documents. For the purpose of organization, each "client" should have it's own index and each "project" of the client has its own namespace within the index.

Each row of the vectorstore has an `ID` field (hash of timestamp + file name), a `VALUES` field (vector representation of the file contents) along with `METADATA` describing the row.

The `METADATA` fields for each chunk is as follows:

- `chunk_id`: The sequential chunk of the file. E.g. File with 3 chunked documents, will have chunk ids 1, 2, 3.
- `name`: Name of the file, including the extension. E.g. "建築基準法施行令.pdf"
- `text`: Actual text values of the document chunk.
- `timestamp`: Epoch timestamp (in microseconds) for when the document chunk was uploaded.

## File storage

Files are stored in a self hosted `Minio` bucket. Each *client-project* pairing has its own bucket.

E.g.:

`client: test, project: hello -> bucket name: test-hello`

The `POST /upload` endpoint will create a bucket for the client-project pairing if it does not already exist with versioning enabled.

# API routes

The RAG app has three routes which can be found under `./src/routers` and accompanying utilities functions found under `./src/utils`. All endpoints are `async`.

## Upload route

`POST /upload`

This endpoint uploads files to a Minio bucket and returns a list of signed URLs. Here is the breakdown:

1. Iterate through the list of files provided in the request
2. Perform checks on each file
3. Ensures that the bucket for the client-project pairing is available, creates a bucket if not.
4. Uploads each file to the bucket in 10MB chunks.
5. Returns a list of presigned URLs and information on if any errors occurred during the request.

The functions interacting with the Minio client are wrapped in a `async_retry` decorator, meaning the operation will be retried a defined number of times with exponential backoff in case an error occurs.

## Create embeddings route

`POST /create_embeddings`

This endpoint creates embeddings and stores them in a Pinecone index given a file. Breakdown is as follows:

1. Downloads the file from the given presigned URL (supports resumable downloads) to a tmp dir on disk.
2. Runs a mock OCR extraction on the downloaded file to produce a langchain Document.
3. Cleans up by deleting the downloaded file from the temporary storage once contents are loaded into memory.
4. Splits the OCR output into smaller chunks.
5. Adds metadata to each chunk and generates unique IDs for each document chunk.
6. Checks if a Pinecone index exists for the client; if not, creates one for the client.
7. Uploads the embeddings to the vector database.

Again, the functions interacting with the Minio client and the Pinecone database are wrapped in a `async_retry` decorator.

> NOTE:
>
> Reading the characters of the JSON sample OCR outputs individually loses newline characters, which would mean we lose some semantic grouping of the text. On top of that, we have to loop a lot in python which is slow. Therefore, I opted to load the entire contents of the sample output into memory all at once, which is most costly in terms of space, but more performant in terms of speed.
>
> - Optimization:
    - Read the "content" of the "analyzeResult" token by token until we reach the token limit of an vector chunk. Recursively find last read separator (new line, period, comma, etc.) and break the text from there. Upload chunk first, then iterate to define the next chunk and repeat. This way we avoid loading the entire content into memory and can upload a set of chunks at a time before flushing.

## Query route

`POST /query`

This route answers a question in natural language about a file given the file name. Here is the breakdown:

1. Retrieves the Pinecone index which serves as a connection using the provided client information.
2. Creates a RAG chain using the retrieved index, project name, file name, and a predefined prompt.
3. Makes LLM call with the query provided in the request along with context from the file.
4. Returns the answer and context used to generate the answer.

# Logging

The application level logger is instantiated in the `./src/__init__.py`. All logging goes through a single logger instance for the app. Log outputs are written to rotating log files under `./etc/logs` and errors will be collected in an error-only log file for ease of monitoring.

Enable `DEBUG` mode by setting the env var in `./etc/.env` to `TRUE`. This will enable logging to stream to STDOUT alongside to being logged into log files under `./etc/logs`. More granular logging is also ensured.

# Tests

Unit tests written with `pytest` are provided under `./test/` directory. The coverage is basic for now as performing local tests is non-trivial for LLM dependent applications. The `upload` route is well covered, the `create_embeddings` route is half covered and the `query` route is less than half covered.

To run the tests simply run:

`pytest -vv`

# CI/CD

This repo is PEP8 compliant and lint checks are ran upon opening a PR to merge into `main` branch. The GHA workflow for lint checks can be found `./.github/workflows/python-app.yml`. Unit tests are also ran as apart of the PR automated checks before merging is allowed.

Docker image building is automated upon pushes to `main` branch and uploaded to a [Docker hub repo](https://hub.docker.com/repository/docker/dychen1/rag_app/general).

> NOTE:
>
> For now, running `create_embeddings` and `query` requests through an image instance will not work properly as I have not yet configured environment variable injection properly for apps running from pre-built Docker images.

# Todo's

`POST /upload`

- Upload file in chunks and resume in case of failure, stitch file together in minio once all chunks are received. Will require versioning for chunks to protect against overwriting existing chunks.

`POST /create_embeddings`

- Implement versioning for chunks and query only latest chunks OR flush all previous chunks relating to a filename if it is being reuploaded.

`POST /query`

- Perform check to see if defined chunk size of each document + question exceeds context window of selected LLM.

`Build`

- Rework environment variable injection. Inject credentials at the docker-compose command line level so that we can use the built image for release deployments.
