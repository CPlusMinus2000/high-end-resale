Set-Location C:\Users\admin\Desktop\Colin\high-end-resale\cmbots
Git pull
$files = @(
  "inventory_bot.py",
  "barcode_bot.py",
  "BarcodeBot Instructions.txt",
  "InventoryBot Instructions.txt",
  "stock_database_bot.py",
  "StockDatabaseBot Instructions.txt"
)

foreach ($file in $files) {
  Copy-Item $file ..\..\..
}

$modules = @(
  "modules/constants.py",
  "modules/filereader.py"
)

foreach ($module in $modules) {
  Copy-Item $module ..\..\..\modules
}