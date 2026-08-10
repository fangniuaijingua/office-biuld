[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$TemplatePath
)

$ErrorActionPreference = 'Stop'

function Get-CommandInfo([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    [ordered]@{
        name = $Name
        available = ($null -ne $command)
        source = if ($command) { $command.Source } else { $null }
    }
}

$resolvedTemplate = Resolve-Path -LiteralPath $TemplatePath -ErrorAction SilentlyContinue
$template = if ($resolvedTemplate) { Get-Item -LiteralPath $resolvedTemplate } else { $null }
$signature = $null
if ($template) {
    $bytes = Get-Content -LiteralPath $template.FullName -AsByteStream -TotalCount 8
    $signature = ($bytes | ForEach-Object { $_.ToString('X2') }) -join ' '
}

$result = [ordered]@{
    checked_at = (Get-Date).ToString('o')
    template = [ordered]@{
        requested_path = $TemplatePath
        exists = ($null -ne $template)
        full_name = if ($template) { $template.FullName } else { $null }
        extension = if ($template) { $template.Extension } else { $null }
        bytes = if ($template) { $template.Length } else { $null }
        last_write_time = if ($template) { $template.LastWriteTime.ToString('o') } else { $null }
        header_hex = $signature
        write_policy = 'read-only; create an output copy before conversion or editing'
    }
    tools = @(
        (Get-CommandInfo 'officecli'),
        (Get-CommandInfo 'soffice'),
        (Get-CommandInfo 'libreoffice'),
        (Get-CommandInfo 'pandoc'),
        (Get-CommandInfo 'python'),
        (Get-CommandInfo 'winword'),
        (Get-CommandInfo 'node'),
        (Get-CommandInfo 'drawio'),
        (Get-CommandInfo 'mmdc'),
        (Get-CommandInfo 'dot'),
        (Get-CommandInfo 'pdftoppm')
    )
    guidance = @(
        'Do not edit a legacy .doc with python-docx.',
        'Prefer a .docx copy created by a compatible Office conversion tool.',
        'This preflight is read-only and does not install tools or write report files.'
    )
}

$result | ConvertTo-Json -Depth 5
