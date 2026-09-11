const API_URL =
    "http://127.0.0.1:8000/api/v1/documents/process";


// =========================================================
// ELEMENTS
// =========================================================

const fileInput =
    document.getElementById("fileInput");

const chooseFileBtn =
    document.getElementById("chooseFileBtn");

const dropZone =
    document.getElementById("dropZone");

const typeCards =
    document.querySelectorAll(".type-card");

const selectedTypeMessage =
    document.getElementById("selectedTypeMessage");


// =========================================================
// DOCUMENT TYPE
// =========================================================

let selectedDocumentType = null;


// =========================================================
// DOCUMENT TYPE SELECTION
// =========================================================

typeCards.forEach(card => {

    card.addEventListener("click", () => {

        // Remove selection from all cards
        typeCards.forEach(item => {
            item.classList.remove("selected");
        });

        // Select clicked card
        card.classList.add("selected");

        // Get backend-compatible value
        selectedDocumentType =
            card.dataset.type;

        // Display selected type
        const displayName =
            card.querySelector("h3").textContent;

        selectedTypeMessage.textContent =
            `Selected: ${displayName}`;

        selectedTypeMessage.classList.add(
            "type-selected"
        );

    });

});


// =========================================================
// CHOOSE FILE BUTTON
// =========================================================

chooseFileBtn.addEventListener(
    "click",
    () => {

        // Don't allow upload without selecting type
        if (!selectedDocumentType) {

            alert(
                "Please select the document type first."
            );

            return;
        }

        fileInput.click();

    }
);


// =========================================================
// FILE INPUT
// =========================================================

fileInput.addEventListener(
    "change",
    () => {

        if (fileInput.files.length > 0) {

            processFile(
                fileInput.files[0]
            );

        }

    }
);


// =========================================================
// DRAG OVER
// =========================================================

dropZone.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        dropZone.classList.add(
            "dragover"
        );

    }
);


// =========================================================
// DRAG LEAVE
// =========================================================

dropZone.addEventListener(
    "dragleave",
    () => {

        dropZone.classList.remove(
            "dragover"
        );

    }
);


// =========================================================
// DROP
// =========================================================

dropZone.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        dropZone.classList.remove(
            "dragover"
        );


        // Require document type
        if (!selectedDocumentType) {

            alert(
                "Please select the document type first."
            );

            return;
        }


        const file =
            event.dataTransfer.files[0];


        if (file) {

            processFile(file);

        }

    }
);


// =========================================================
// PROCESS FILE
// =========================================================

async function processFile(file) {

    // -----------------------------------------------------
    // Validate file extension
    // -----------------------------------------------------

    const allowedExtensions = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png"
    ];


    const fileName =
        file.name.toLowerCase();


    const isAllowed =
        allowedExtensions.some(
            extension =>
                fileName.endsWith(extension)
        );


    if (!isAllowed) {

        alert(
            "Please upload a PDF, JPG or PNG file."
        );

        return;

    }


    // -----------------------------------------------------
    // Make sure type exists
    // -----------------------------------------------------

    if (!selectedDocumentType) {

        alert(
            "Please select the document type first."
        );

        return;

    }


    // -----------------------------------------------------
    // Disable button
    // -----------------------------------------------------

    chooseFileBtn.disabled = true;


    chooseFileBtn.innerHTML = `
        <span>Processing document...</span>
        <span class="button-arrow">⟳</span>
    `;


    // -----------------------------------------------------
    // Create form data
    // -----------------------------------------------------

    const formData =
        new FormData();


    // IMPORTANT:
    // Backend expects "file"
    formData.append(
        "file",
        file
    );


    // IMPORTANT:
    // Backend expects one of:
    //
    // invoice
    // balance_sheet
    // profit_and_loss
    // cash_flow_statement
    //
    formData.append(
        "document_type",
        selectedDocumentType
    );


    // -----------------------------------------------------
    // Send request
    // -----------------------------------------------------

    try {

        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",
                    body: formData
                }
            );


        // -------------------------------------------------
        // Parse response
        // -------------------------------------------------

        let result;

        const contentType =
            response.headers.get(
                "content-type"
            ) || "";


        if (
            contentType.includes(
                "application/json"
            )
        ) {

            result =
                await response.json();

        } else {

            const text =
                await response.text();

            result = {
                detail:
                    text ||
                    "Unknown server response."
            };

        }


        // -------------------------------------------------
        // Handle backend error
        // -------------------------------------------------

        if (!response.ok) {

            let errorMessage =
                "Document processing failed.";


            if (result.detail) {

                if (
                    typeof result.detail ===
                    "string"
                ) {

                    errorMessage =
                        result.detail;

                } else {

                    errorMessage =
                        JSON.stringify(
                            result.detail,
                            null,
                            2
                        );

                }

            } else if (result.message) {

                errorMessage =
                    result.message;

            } else {

                errorMessage =
                    JSON.stringify(
                        result,
                        null,
                        2
                    );

            }


            console.error(
                "Backend error:",
                result
            );


            throw new Error(
                `Server returned ${response.status}\n\n${errorMessage}`
            );

        }


        // -------------------------------------------------
        // Store result
        // -------------------------------------------------

        sessionStorage.setItem(
            "documentResult",
            JSON.stringify(result)
        );


        sessionStorage.setItem(
            "documentName",
            file.name
        );


        sessionStorage.setItem(
            "selectedDocumentType",
            selectedDocumentType
        );


        // -------------------------------------------------
        // Go to result page
        // -------------------------------------------------

        window.location.href =
            "result.html";

    }


    catch (error) {

        console.error(
            "Document processing error:",
            error
        );


        let message =
            error.message;


        if (
            error instanceof TypeError &&
            error.message
                .toLowerCase()
                .includes("fetch")
        ) {

            message =
                "Unable to connect to the Document Intelligence API.\n\n" +
                "Please make sure the FastAPI server is running at:\n" +
                "http://127.0.0.1:8000";

        }


        alert(
            "Unable to process document.\n\n" +
            message
        );


        // Re-enable button
        chooseFileBtn.disabled =
            false;


        chooseFileBtn.innerHTML = `
            <span>Choose Document</span>
            <span class="button-arrow">→</span>
        `;

    }

}
// =====================================================
// DOCUMENT HISTORY
// =====================================================

async function loadDocumentHistory() {

    const historyContainer =
        document.getElementById("documentHistory");

    const historyCount =
        document.getElementById("historyCount");

    if (!historyContainer) return;

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/api/v1/documents"
        );

        if (!response.ok) {
            throw new Error("Failed to load document history");
        }

        const result = await response.json();

        const documents = result.documents || [];

        historyCount.textContent =
            `${documents.length} document${documents.length === 1 ? "" : "s"}`;

        if (documents.length === 0) {

            historyContainer.innerHTML = `
                <div class="history-empty">
                    No documents processed yet.
                </div>
            `;

            return;
        }

        historyContainer.innerHTML = documents.map(document => {

            const status = document.processing_status || "UNKNOWN";

            let statusClass = "status-neutral";
            let statusIcon = "•";

            if (status === "PASS") {
                statusClass = "status-pass";
                statusIcon = "✓";
            }
            else if (
                status === "FAILED" ||
                status === "FAILED_VALIDATION" ||
                status === "AI_EXTRACTION_FAILED"
            ) {
                statusClass = "status-fail";
                statusIcon = "×";
            }
            else if (status === "NOT_APPLICABLE") {
                statusClass = "status-warning";
                statusIcon = "!";
            }

            const typeNames = {
                invoice: "Invoice",
                balance_sheet: "Balance Sheet",
                profit_and_loss: "Profit & Loss",
                cash_flow_statement: "Cash Flow Statement"
            };

            const typeName =
                typeNames[document.document_type] ||
                document.document_type;

            const uploadedDate = document.uploaded_at
                ? new Date(document.uploaded_at).toLocaleString()
                : "—";

            return `
                <div
                    class="history-card"
                    onclick="openStoredDocument(${document.id})"
                >

                    <div class="history-document-icon">
                        📄
                    </div>

                    <div class="history-document-info">

                        <h3>
                            ${document.filename}
                        </h3>

                        <p>
                            ${typeName}
                            <span>•</span>
                            ${uploadedDate}
                        </p>

                    </div>

                    <div class="history-status ${statusClass}">
                        <span>${statusIcon}</span>
                        ${status.replaceAll("_", " ")}
                    </div>

                </div>
            `;

        }).join("");

    }
    catch (error) {

        console.error(
            "Document history error:",
            error
        );

        historyContainer.innerHTML = `
            <div class="history-empty">
                Unable to load document history.
            </div>
        `;
    }
}


// Load history when dashboard opens
if (document.getElementById("documentHistory")) {
    loadDocumentHistory();
}

// =====================================================
// OPEN STORED DOCUMENT
// =====================================================

function openStoredDocument(documentId) {

    const fileUrl =
        `http://127.0.0.1:8000/api/v1/documents/file/${documentId}`;

    window.open(fileUrl, "_blank");
}