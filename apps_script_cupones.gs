// Pega este código completo en el editor de Apps Script de tu Google Sheet.
// Reemplaza esta clave si quieres, pero avísame cuál usaste.
var CLAVE_SECRETA = "superseller-cupones-2026";

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);

    if (body.token !== CLAVE_SECRETA) {
      return ContentService.createTextOutput(JSON.stringify({ error: "clave inválida" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(body.sheet);
    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({ error: "no existe la pestaña: " + body.sheet }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    if (body.action === "append_row") {
      sheet.appendRow(body.values);
    } else if (body.action === "append_rows") {
      body.rows.forEach(function (row) {
        sheet.appendRow(row);
      });
    } else if (body.action === "set_cell") {
      sheet.getRange(body.cell).setValue(body.value);
    } else {
      return ContentService.createTextOutput(JSON.stringify({ error: "acción desconocida: " + body.action }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
