[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$InputPath,

    [Parameter(Mandatory)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$inputItem = Get-Item -LiteralPath $InputPath
$outputFull = [System.IO.Path]::GetFullPath($OutputPath)
if ($inputItem.FullName -eq $outputFull) {
    throw 'Input and output must be different files.'
}

$outputDirectory = Split-Path -Parent $outputFull
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
if (Test-Path -LiteralPath $outputFull) {
    throw "Refusing to overwrite existing output: $outputFull"
}

$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    # ReadOnly prevents Word from altering the legacy source copy.
    $document = $word.Documents.Open($inputItem.FullName, $false, $true)
    # wdFormatXMLDocument = 12 (.docx)
    $document.SaveAs2($outputFull, 12)
    $document.Close(0)
    $document = $null
}
finally {
    if ($document) {
        $document.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document)
    }
    if ($word) {
        $word.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

$outputItem = Get-Item -LiteralPath $outputFull
$header = Get-Content -LiteralPath $outputFull -AsByteStream -TotalCount 4
if ((($header | ForEach-Object { $_.ToString('X2') }) -join ' ') -ne '50 4B 03 04') {
    throw 'Word did not produce an OOXML/ZIP .docx output.'
}

[ordered]@{
    input = $inputItem.FullName
    output = $outputItem.FullName
    output_bytes = $outputItem.Length
    format = 'OOXML .docx (Word SaveAs2 FileFormat=12)'
    source_opened_read_only = $true
} | ConvertTo-Json
