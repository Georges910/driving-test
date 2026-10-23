/** Bound to a private Google Sheet. Deploy as Web App: execute as Me, access Anyone.
 * Public endpoint accepts training results; private admin dashboard runs ONLY in Sheets.
 * Never expose the Sheet or Apps Script editor to students.
 */
const SHEET_NAME = 'Scores';
const HEADERS = ['Submitted At','Attempt ID','Full Name','Score','Total','Percent','Passed','Duration (seconds)','Wrong Question IDs'];
function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) { sh = ss.insertSheet(SHEET_NAME); sh.appendRow(HEADERS); sh.setFrozenRows(1); }
  return sh;
}
function text_(value, max) {
  const s = String(value == null ? '' : value).trim().slice(0,max);
  // Prevent spreadsheet formula injection when student-provided text is written to cells.
  return /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
}
function doPost(e) {
  // A public static website cannot provide trusted exam results: submissions are unverified.
  try {
    if (!e || !e.postData || e.postData.contents.length > 12000) throw Error('Invalid payload');
    const d = JSON.parse(e.postData.contents);
    const name = text_(d.name,60);
    const score = Number(d.score), total = Number(d.total), seconds = Number(d.seconds);
    if (name.length < 2 || !Number.isInteger(score) || total !== 30 || score < 0 || score > total ||
        !Number.isInteger(seconds) || seconds < 0 || seconds > 900 ||
        !Array.isArray(d.wrong) || d.wrong.length !== total-score ||
        d.wrong.some(x => !Number.isInteger(Number(x)) || Number(x)<0 || Number(x)>10000)) throw Error('Invalid result');
    const attempt = /^[a-zA-Z0-9-]{8,80}$/.test(String(d.attemptId||'')) ? String(d.attemptId) : Utilities.getUuid();
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const sh = sheet_();
      // Idempotency: retrying the same attempt should not create another history entry.
      const existing = sh.getLastRow() > 1 ? sh.getRange(2,2,sh.getLastRow()-1,1).createTextFinder(attempt).matchEntireCell(true).findNext() : null;
      if (!existing) sh.appendRow([new Date(),attempt,name,score,total,Math.round(score/total*100),score>=24?'Yes':'No',seconds,d.wrong.join(', ')]);
    } finally { lock.releaseLock(); }
    return ContentService.createTextOutput('accepted');
  } catch (err) {
    console.error(err);
    return ContentService.createTextOutput('rejected');
  }
}
function doGet() { return ContentService.createTextOutput('Exam submission endpoint. Admin history is private in Google Sheets.'); }
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Driving Exam').addItem('Open Admin Dashboard','showDashboard').addToUi();
}
function showDashboard() {
  const html = HtmlService.createHtmlOutputFromFile('Dashboard').setTitle('Driving Exam — Admin');
  SpreadsheetApp.getUi().showSidebar(html);
}
function getExamHistory() {
  // This function is only called from the Sheets sidebar under the editor's Google identity.
  const sh = sheet_(), rows = sh.getLastRow() < 2 ? [] : sh.getRange(2,1,sh.getLastRow()-1,9).getValues();
  return rows.map(r => ({date: r[0] instanceof Date ? r[0].toISOString() : String(r[0]), id:String(r[1]), name:String(r[2]), score:Number(r[3]), total:Number(r[4]), percent:Number(r[5]), passed:String(r[6])==='Yes', seconds:Number(r[7]), wrong:String(r[8])})).reverse();
}
