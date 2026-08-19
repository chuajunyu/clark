const printButton = document.querySelector("#open-print-controls");
const pdfFrame = document.querySelector("#pdf-frame");
const fallback = document.querySelector("#open-pdf-fallback");

printButton?.addEventListener("click", () => {
  try {
    pdfFrame.contentWindow.focus();
    pdfFrame.contentWindow.print();
  } catch (_) {
    fallback.click();
  }
});

