import asyncio
import json
from os import getenv
from sanic import HTTPResponse, Request, Sanic
import aiohttp
from aiohttp.web import StreamResponse, Response

app = Sanic(__name__)

async def forward_request(req: Request, path:str):
    forward = req.headers.get("X-Forwarded-To", "").replace("http://", "").replace("https://", "") or None
    callback = req.headers.get("X-Callback-Url")
    echo = req.headers.get("X-Echo")

    new_headers = dict(req.headers)
    new_headers.pop("X-Forwarded-To", None)
    new_headers.pop("X-Callback-Url", None)
    new_headers.pop("X-Echo", None)
    new_headers['host'] = forward
    
    if forward:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(0)) as session:
            print("Forwarding request to", forward, "with callback to", callback)
            async with session.request(
                req.method,
                f"https://{forward}/{path}",
                data=req.body,
                headers=new_headers,
            ) as resp:
                data = await resp.read()
                print(f"Got data, {len(data)} bytes")
                returned_headers = dict(resp.headers)
                returned_status = resp.status

                if echo:
                    returned_headers["X-Echo"] = echo

                if callback:
                    print("Callback, sending to", callback)
                    async for chunk in resp.content.iter_any():
                        async with aiohttp.ClientSession() as session:
                          callback_resp = await session.request(
                              "POST",
                              callback,
                              data=chunk,
                              headers=returned_headers
                          )
                          print("Got response", callback_resp.status, callback_resp.headers)
                    print("Done sending data, terminating")
                    return HTTPResponse(body="OK", status=200)
                else:
                    print("No callback, sending back data")
                    return HTTPResponse(body=await resp.read(), headers=returned_headers, status=returned_status)


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def index(req: Request, path: str):
    if req.headers.get("X-Callback-Url"):
      asyncio.create_task(forward_request(req, path))
      return HTTPResponse(body="CREATED", status=201)
    return await forward_request(req, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(getenv("PORT", 8000)), debug=True)

