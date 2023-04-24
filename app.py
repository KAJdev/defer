import json
from os import getenv
from sanic import HTTPResponse, Request, Sanic
import aiohttp

app = Sanic(__name__)


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def index(req: Request, path: str):
    forward = req.headers.get("X-Forwarded-To", "").replace("http://", "").replace("https://", "") or None
    callback = req.headers.get("X-Callback-Url")
    method = req.headers.get("X-Forwarded-Method") or "POST"
    echo = req.headers.get("X-Echo")

    new_headers = dict(req.headers)
    new_headers.pop("X-Forwarded-To", None)
    new_headers.pop("X-Callback-Url", None)
    new_headers.pop("X-Forwarded-Method", None)
    new_headers.pop("X-Echo", None)
    new_headers['host'] = forward
    
    if forward:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(0)) as session:
            async with session.request(
                req.method,
                f"https://{forward}/{path}",
                data=req.body,
                headers=new_headers,
            ) as resp:
                data = await resp.read()
                print(len(data))
                returned_headers = dict(resp.headers)
                returned_status = resp.status

                if echo:
                    returned_headers["X-Echo"] = echo

                if callback:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(0)) as callback_session:
                        response = aiohttp.StreamResponse()
                        response.headers.update(returned_headers)
                        response.set_status(returned_status)

                        await response.prepare(req)
                        async for chunk in resp.content.iter_chunked(4096):
                            await response.write(chunk)
                            await callback_session.request(
                                method,
                                callback,
                                data=chunk,
                                headers=returned_headers
                            )

                        await response.write_eof()
                        return response
                else:
                    print("No callback, sending back data")
                    return HTTPResponse(body=await resp.read(), headers=returned_headers, status=returned_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(getenv("PORT", 8000)), debug=True)

