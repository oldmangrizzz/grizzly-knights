// ConvexClient — minimal transport over Convex's HTTP API.
// Calls public queries/mutations on the (local) Convex backend. WebGL-safe:
// uses UnityWebRequest + coroutines, no threads.
//
// Convex HTTP API:
//   POST {base}/api/query     body { path, args, format:"json" }  -> { status:"success", value } | { status:"error", errorMessage }
//   POST {base}/api/mutation  (same shape)
using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json.Linq;

public class ConvexClient
{
    private readonly string baseUrl;

    public ConvexClient(string baseUrl)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
    }

    /// <summary>Run a public Convex query. done(value, error) — exactly one is non-null.</summary>
    public IEnumerator Query(string path, object args, Action<JToken, string> done)
    {
        yield return Post("/api/query", path, args, done);
    }

    /// <summary>Run a public Convex mutation.</summary>
    public IEnumerator Mutation(string path, object args, Action<JToken, string> done)
    {
        yield return Post("/api/mutation", path, args, done);
    }

    private IEnumerator Post(string endpoint, string path, object args, Action<JToken, string> done)
    {
        var body = new JObject
        {
            ["path"] = path,
            ["args"] = args == null ? new JObject() : JToken.FromObject(args),
            ["format"] = "json",
        };
        byte[] raw = Encoding.UTF8.GetBytes(body.ToString(Newtonsoft.Json.Formatting.None));

        using (var req = new UnityWebRequest(baseUrl + endpoint, "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(raw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            yield return req.SendWebRequest();

#if UNITY_2020_2_OR_NEWER
            bool ok = req.result == UnityWebRequest.Result.Success;
#else
            bool ok = !req.isNetworkError && !req.isHttpError;
#endif
            if (!ok)
            {
                done?.Invoke(null, $"HTTP {req.responseCode} {req.error}: {req.downloadHandler.text}");
                yield break;
            }

            JObject resp;
            try { resp = JObject.Parse(req.downloadHandler.text); }
            catch (Exception e) { done?.Invoke(null, "JSON parse error: " + e.Message + " :: " + req.downloadHandler.text); yield break; }

            string status = (string)resp["status"];
            if (status == "success") done?.Invoke(resp["value"], null);
            else done?.Invoke(null, "Convex error: " + (string)resp["errorMessage"]);
        }
    }
}
