$port = 8000
$path = "d:\Semester 6\MICRO\Kuis"
$ip = "10.27.220.55"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
$listener.Prefixes.Add("http://127.0.0.1:$port/")
$listener.Prefixes.Add("http://${ip}:${port}/")
$listener.Prefixes.Add("http://+:${port}/")  # Listen on all interfaces
$listener.Start()

Write-Host "Server berjalan di http://localhost:$port/"
Write-Host "Tekan Ctrl+C untuk berhenti"

while ($listener.IsListening) {
    $context = $listener.GetContext()
    $request = $context.Request
    $response = $context.Response

    $localPath = $request.Url.LocalPath
    if ($localPath -eq "/") { $localPath = "/kuis_cerdas_cermat_multiplayer.html" }

    $filePath = Join-Path $path $localPath.TrimStart("/")

    if (Test-Path $filePath -PathType Leaf) {
        $content = Get-Content $filePath -Raw -Encoding UTF8
        $response.ContentType = if ($filePath.EndsWith(".html")) { "text/html; charset=utf-8" } elseif ($filePath.EndsWith(".css")) { "text/css" } elseif ($filePath.EndsWith(".js")) { "application/javascript" } else { "application/octet-stream" }
        $buffer = [System.Text.Encoding]::UTF8.GetBytes($content)
        $response.ContentLength64 = $buffer.Length
        $response.OutputStream.Write($buffer, 0, $buffer.Length)
    } else {
        $response.StatusCode = 404
        $notFound = "<h1>404 - File Not Found</h1>"
        $buffer = [System.Text.Encoding]::UTF8.GetBytes($notFound)
        $response.OutputStream.Write($buffer, 0, $buffer.Length)
    }

    $response.OutputStream.Close()
}

$listener.Stop()