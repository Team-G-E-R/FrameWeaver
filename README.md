# GameAssetsGenerator

How to strup:

run :
doker compose build
docker compose up -d


then:

$uid = "0de06f7f-41d6-4524-bb97-fae4efedd30d"
curl.exe -s -X POST "http://localhost:8000/api/jobs" -H "Content-Type: application/json" -H "X-User-Id: $uid" --data-binary "@payload.json"