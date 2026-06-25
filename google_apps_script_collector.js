function doPost(e) {
  try {
    var SHEET_ID = "11Gkj4u-S2YncfEnfvJXJQFonLyblD0Sw1VxIfzA0O_I";
    var SHEET_NAME = "COMPILACION OFERTAS";

    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sheet = ss.getSheetByName(SHEET_NAME);

    if (!sheet) {
      throw new Error("No se encontró la pestaña '" + SHEET_NAME + "'");
    }

    var items = JSON.parse(e.postData.contents);
    var timestamp = new Date().toLocaleString("es-MX");

    // Encontrar la primera fila vacía (después del header)
    var lastRow = sheet.getLastRow();
    var startRow = lastRow + 1;

    // Agregar productos empezando desde columna B
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var rowData = [
        timestamp,                                      // B: FECHA
        "",                                             // C: ALEATORIO (vacío)
        item.img || item.image || "",                   // D: IMAGEN
        item.link || "",                                // E: LINK
        item.title || "",                               // F: TITULO
        item.price_original || 0,                       // G: PRECIO ORIGINAL
        item.price_discounted || item.price || 0,       // H: PRECIO PROMOCION
        (item.descuento_pct || item.discount || 0) + "%", // I: DESCUENTO
        item.link || "",                                // J: LINK AFILIADO
        "",                                             // K: TIPO DE OFERTA (vacío)
        "Amazon"                                        // L: CANAL
      ];

      // Escribir desde columna B (índice 2)
      var range = sheet.getRange(startRow + i, 2, 1, rowData.length);
      range.setValues([rowData]);
    }

    var result = {
      success: true,
      rows: items.length,
      sheetUrl: ss.getUrl()
    };

    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    var errorResult = {
      success: false,
      error: error.toString()
    };
    return ContentService.createTextOutput(JSON.stringify(errorResult)).setMimeType(ContentService.MimeType.JSON);
  }
}
