// =====================================================
// LOAD DOCUMENT RESULT
// =====================================================

const result =
    JSON.parse(
        sessionStorage.getItem("documentResult")
    );

const documentName =
    sessionStorage.getItem("documentName") ||
    "Document";

// =====================================================
// DOCUMENT PREVIEW
// =====================================================

const previewContainer = document.getElementById("documentPreview");
const previewFileName = document.getElementById("previewFileName");
const previewFileType = document.getElementById("previewFileType");

if (previewFileName) {
    previewFileName.textContent =
        result.document_name || documentName;
}

if (result.document_storage && previewContainer) {
    const storedPath = result.document_storage.file_path;

    const fileUrl =
    `/api/v1/documents/file/${result.document_storage.id}`;

    const fileExtension =
        storedPath.split(".").pop().toLowerCase();

    if (fileExtension === "pdf") {

        previewFileType.textContent = "PDF document";

        previewContainer.innerHTML = `
            <iframe
                src="${fileUrl}"
                class="document-preview-frame"
                title="Document preview">
            </iframe>
        `;

    } else if (
        ["jpg", "jpeg", "png"].includes(fileExtension)
    ) {

        previewFileType.textContent = "Image document";

        previewContainer.innerHTML = `
            <img
                src="${fileUrl}"
                class="document-preview-image"
                alt="Uploaded document preview">
        `;

    } else {

        previewFileType.textContent = "Document";

        previewContainer.innerHTML = `
            <a
                href="${fileUrl}"
                target="_blank"
                class="preview-open-link">
                Open document
            </a>
        `;
    }

} else {

    if (previewContainer) {
        previewContainer.innerHTML = `
            <div class="preview-empty">
                Document preview unavailable.
            </div>
        `;
    }
}

// =====================================================
// SAFETY CHECK
// =====================================================

if (!result) {

    alert("No document result found.");

    window.location.href =
        "index.html";

    throw new Error(
        "No document result found"
    );
}


// =====================================================
// HELPER FUNCTIONS
// =====================================================

function formatLabel(text) {

    return text
        .replace(/_/g, " ")
        .replace(/\b\w/g, letter =>
            letter.toUpperCase()
        );
}


function formatValue(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    return String(value);
}


// =====================================================
// DOCUMENT SUMMARY
// =====================================================

document.getElementById(
    "documentName"
).textContent =
    result.document_name ||
    documentName;


const typeNames = {

    invoice:
        "Invoice",

    balance_sheet:
        "Balance Sheet",

    profit_and_loss:
        "Profit & Loss",

    cash_flow_statement:
        "Cash Flow Statement"
};


document.getElementById(
    "documentType"
).textContent =

    typeNames[
        result.document_type
    ] ||

    result.document_type ||

    "—";


// =====================================================
// OVERALL VALIDATION STATUS
// =====================================================

const financialValidation =
    result.financial_validation ||
    {};

const overallStatus =
    financialValidation.overall_status ||
    "NOT_APPLICABLE";


document.getElementById(
    "overallStatus"
).textContent =
    overallStatus;


// =====================================================
// AI EXTRACTION DATA
// =====================================================

const aiExtraction =
    result.ai_extraction ||
    {};

const extractedData =
    aiExtraction.data ||
    {};

const fields =
    extractedData.fields ||
    {};

const lineItems =
    extractedData.line_items ||
    [];


// =====================================================
// DOCUMENT FIELDS
// =====================================================

const fieldsContainer =
    document.getElementById(
        "fieldsContainer"
    );

const fieldCount =
    document.getElementById(
        "fieldCount"
    );


const validFields =
    Object.entries(fields).filter(
        ([key, field]) =>

            field !== null &&
            field !== undefined
    );


fieldCount.textContent =
    `${validFields.length} fields`;


if (
    validFields.length === 0
) {

    fieldsContainer.innerHTML = `

        <div class="empty-state">

            No fields were extracted.

        </div>

    `;

} else {

    fieldsContainer.innerHTML =
        "";


    validFields.forEach(
        ([key, field]) => {

            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "field-card";


            // -----------------------------------------
            // AI FIELD STRUCTURE
            // -----------------------------------------

            let value =
                field;

            let evidence =
                [];

            let confidence =
                null;


            if (
                typeof field === "object" &&
                field !== null
            ) {

                value =
                    field.value ??
                    null;

                evidence =
                    Array.isArray(
                        field.evidence
                    )
                        ? field.evidence
                        : [];

                confidence =
                    field.confidence ??
                    null;
            }


            // -----------------------------------------
            // EVIDENCE
            // -----------------------------------------

            let evidenceHTML =
                "";


            if (
                evidence.length > 0
            ) {

                const firstEvidence =
                    evidence[0];


                evidenceHTML = `

                    <div class="field-evidence">

                        <span class="evidence-icon">
                            ◉
                        </span>

                        <span>
                            ${
                                firstEvidence.source_text ||
                                ""
                            }
                        </span>

                        ${
                            firstEvidence.page_number
                                ? `
                                    <span>
                                        · Page
                                        ${
                                            firstEvidence.page_number
                                        }
                                    </span>
                                  `
                                : ""
                        }

                    </div>

                `;
            }


            // -----------------------------------------
            // CONFIDENCE
            // -----------------------------------------

            let confidenceHTML =
                "";


            if (
                confidence !== null &&
                confidence !== undefined
            ) {

                confidenceHTML = `

                    <div class="field-confidence">

                        ${
                            Math.round(
                                Number(confidence) *
                                100
                            )
                        }% confidence

                    </div>

                `;
            }


            // -----------------------------------------
            // FINAL FIELD CARD
            // -----------------------------------------

            card.innerHTML = `

                <div class="field-label">

                    ${formatLabel(key)}

                </div>


                <div class="field-value">

                    ${formatValue(value)}

                </div>


                ${evidenceHTML}


                ${confidenceHTML}

            `;


            fieldsContainer.appendChild(
                card
            );
        }
    );
}


// =====================================================
// LINE ITEMS
// =====================================================

const lineItemsSection =
    document.getElementById(
        "lineItemsSection"
    );

const lineItemsBody =
    document.getElementById(
        "lineItemsBody"
    );

const itemCount =
    document.getElementById(
        "itemCount"
    );


itemCount.textContent =
    `${lineItems.length} items`;


if (
    lineItems.length === 0
) {

    lineItemsSection.style.display =
        "none";

} else {

    lineItemsSection.style.display =
        "block";


    lineItemsBody.innerHTML =

        lineItems
            .map(item => {


                // -------------------------------------
                // HANDLE NESTED AI FIELD OBJECTS
                // -------------------------------------

                function cellValue(
                    value
                ) {

                    if (
                        value &&
                        typeof value ===
                            "object"
                    ) {

                        return (
                            value.value ??
                            "—"
                        );
                    }


                    return (
                        value ??
                        "—"
                    );
                }


                return `

                    <tr>

                        <td>
                            ${
                                cellValue(
                                    item.description
                                )
                            }
                        </td>


                        <td>
                            ${
                                cellValue(
                                    item.quantity
                                )
                            }
                        </td>


                        <td>
                            ${
                                cellValue(
                                    item.unit_price
                                )
                            }
                        </td>


                        <td>
                            ${
                                cellValue(
                                    item.tax
                                )
                            }
                        </td>


                        <td>
                            ${
                                cellValue(
                                    item.line_total
                                )
                            }
                        </td>

                    </tr>

                `;

            })
            .join("");
}


// =====================================================
// FINANCIAL VALIDATION CHECKS
// =====================================================

const checks =
    financialValidation.checks ||
    [];


const validationContainer =
    document.getElementById(
        "validationContainer"
    );

const validationCount =
    document.getElementById(
        "validationCount"
    );


validationCount.textContent =
    `${checks.length} checks`;


if (
    checks.length === 0
) {

    validationContainer.innerHTML = `

        <div class="empty-state">

            No validation checks available.

        </div>

    `;

} else {

    validationContainer.innerHTML =

        checks
            .map(check => {

                const status =
                    check.status ||
                    "NOT_APPLICABLE";


                const statusClass =
                    status.toLowerCase();


                return `

                    <div class="validation-card">


                        <!-- =========================
                             CHECK HEADER
                        ========================== -->

                        <div class="validation-card-top">


                            <div class="validation-title">


                                <span
                                    class="validation-icon"
                                >

                                    ${
                                        status ===
                                        "PASS"
                                            ? "✓"
                                            : "!"

                                    }

                                </span>


                                <span>

                                    ${
                                        check.formula ||
                                        "Validation check"
                                    }

                                </span>


                            </div>


                            <span
                                class="
                                    validation-badge
                                    ${statusClass}
                                "
                            >

                                ${status}

                            </span>


                        </div>



                        <!-- =========================
                             CHECK VALUES
                        ========================== -->

                        <div class="validation-values">


                            <div
                                class="
                                    validation-value
                                "
                            >

                                <span>
                                    Reported
                                </span>

                                <strong>
                                    ${
                                        check.reported ??
                                        "—"
                                    }
                                </strong>

                            </div>


                            <div
                                class="
                                    validation-value
                                "
                            >

                                <span>
                                    Calculated
                                </span>

                                <strong>
                                    ${
                                        check.calculated ??
                                        "—"
                                    }
                                </strong>

                            </div>


                            <div
                                class="
                                    validation-value
                                "
                            >

                                <span>
                                    Variance
                                </span>

                                <strong>
                                    ${
                                        check.variance ??
                                        "—"
                                    }
                                </strong>

                            </div>


                        </div>


                    </div>

                `;

            })
            .join("");
}


// =====================================================
// EXTRACTION NOTES
// =====================================================

const notes =
    extractedData.extraction_notes ||
    [];


const notesSection =
    document.getElementById(
        "notesSection"
    );

const notesContainer =
    document.getElementById(
        "notesContainer"
    );


if (
    notes.length === 0
) {

    notesSection.style.display =
        "none";

} else {

    notesSection.style.display =
        "block";


    notesContainer.innerHTML =

        notes
            .map(note => `

                <div class="note-item">

                    ${note}

                </div>

            `)
            .join("");
}


// =====================================================
// DEBUG INFORMATION
// =====================================================

console.log(
    "Full document result:",
    result
);

console.log(
    "Extracted fields:",
    fields
);

console.log(
    "Line items:",
    lineItems
);

console.log(
    "Validation checks:",
    checks
);
// =====================================================
// DOWNLOAD VALIDATION REPORT
// =====================================================

function downloadValidationReport() {

    const result =
        JSON.parse(sessionStorage.getItem("documentResult"));

    if (!result) {
        alert("Validation result not available.");
        return;
    }

    const report = {
        document_name: result.document_name,
        document_type: result.document_type,
        processing_status: result.processing_status,

        extracted_data:
            result.ai_extraction?.data || {},

        financial_validation:
            result.financial_validation || {},

        file_validation:
            result.file_validation || {},

        text_extraction:
            result.text_extraction || {}
    };

    const jsonData =
        JSON.stringify(report, null, 2);

    const blob = new Blob(
        [jsonData],
        { type: "application/json" }
    );

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement("a");

    link.href = url;

    const fileName =
        result.document_name
            ? result.document_name.replace(/\.[^/.]+$/, "")
            : "document";

    link.download =
        `${fileName}_validation_report.json`;

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}