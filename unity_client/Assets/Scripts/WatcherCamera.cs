// WatcherCamera — the four ways Uatu watches the world.
//   1  Overhead   : the god's-eye in the sky (default). WASD pans, scroll zooms.
//   2  Fly        : free invisible flight. WASD + Q/E up-down, hold RIGHT-MOUSE to look, scroll = speed.
//   (click anyone) Follow : anchor third-person to one soul; RIGHT-MOUSE orbits, scroll dollies. Esc releases.
using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(Camera))]
public class WatcherCamera : MonoBehaviour
{
    public enum Mode { Overhead, Fly, Follow }
    public Mode mode = Mode.Overhead;

    [Header("Feel")]
    public float flySpeed = 20f, lookSens = 2.6f, panSpeed = 34f, zoomSpeed = 40f;
    public float overheadHeight = 90f, followDist = 6.5f;

    Camera cam;
    AgentSpawner spawner;
    Transform followTarget;
    float yaw, pitch, orbitYaw, orbitPitch = 18f, curFollowDist;

    void Start()
    {
        cam = GetComponent<Camera>();
        spawner = FindObjectOfType<AgentSpawner>();
        curFollowDist = followDist;
        EnterOverhead();
    }

    Vector3 Center()
    {
        if (spawner != null)
        {
            Vector3 sum = Vector3.zero; int n = 0;
            foreach (var kv in spawner.Roots) { if (kv.Value) { sum += kv.Value.transform.position; n++; } }
            if (n > 0) return sum / n;
        }
        return new Vector3(45f, 0f, -45f);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1)) EnterOverhead();
        if (Input.GetKeyDown(KeyCode.Alpha2)) EnterFly();
        if (Input.GetKeyDown(KeyCode.Escape) && mode == Mode.Follow) EnterFly();

        if (Input.GetMouseButtonDown(0))
        {
            var t = NearestToMouse();
            if (t != null) { followTarget = t; mode = Mode.Follow; orbitYaw = transform.eulerAngles.y; }
        }

        if (mode == Mode.Overhead) Overhead();
        else if (mode == Mode.Fly) Fly();
        else Follow();
    }

    void EnterOverhead()
    {
        mode = Mode.Overhead;
        var c = Center();
        transform.position = new Vector3(c.x, overheadHeight, c.z + 6f);
        transform.rotation = Quaternion.Euler(82f, 0f, 0f);
    }

    void EnterFly()
    {
        mode = Mode.Fly;
        var e = transform.eulerAngles; yaw = e.y; pitch = e.x > 180 ? e.x - 360 : e.x;
    }

    void Overhead()
    {
        float h = Input.GetAxisRaw("Horizontal"), v = Input.GetAxisRaw("Vertical");
        transform.position += new Vector3(h, 0, v) * panSpeed * Time.deltaTime;
        float sc = Input.mouseScrollDelta.y;
        if (Mathf.Abs(sc) > 0.01f)
        {
            float y = Mathf.Clamp(transform.position.y - sc * zoomSpeed, 14f, 180f);
            transform.position = new Vector3(transform.position.x, y, transform.position.z);
        }
    }

    void Fly()
    {
        if (Input.GetMouseButton(1))
        {
            yaw += Input.GetAxis("Mouse X") * lookSens;
            pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * lookSens, -89f, 89f);
            transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
        }
        float spd = flySpeed * (Input.GetKey(KeyCode.LeftShift) ? 3f : 1f) * Time.deltaTime;
        Vector3 m = new Vector3(Input.GetAxisRaw("Horizontal"), 0, Input.GetAxisRaw("Vertical"));
        transform.position += transform.TransformDirection(m) * spd;
        if (Input.GetKey(KeyCode.E)) transform.position += Vector3.up * spd;
        if (Input.GetKey(KeyCode.Q)) transform.position += Vector3.down * spd;
    }

    void Follow()
    {
        if (followTarget == null) { EnterFly(); return; }
        if (Input.GetMouseButton(1))
        {
            orbitYaw += Input.GetAxis("Mouse X") * lookSens;
            orbitPitch = Mathf.Clamp(orbitPitch - Input.GetAxis("Mouse Y") * lookSens, -8f, 72f);
        }
        float sc = Input.mouseScrollDelta.y;
        if (Mathf.Abs(sc) > 0.01f) curFollowDist = Mathf.Clamp(curFollowDist - sc * 2f, 2.5f, 22f);
        Vector3 focus = followTarget.position + Vector3.up * 1.4f;
        Vector3 desired = focus + Quaternion.Euler(orbitPitch, orbitYaw, 0) * new Vector3(0, 0, -curFollowDist);
        transform.position = Vector3.Lerp(transform.position, desired, Time.deltaTime * 6f);
        transform.LookAt(focus);
    }

    Transform NearestToMouse()
    {
        if (spawner == null) return null;
        float best = 60f; Transform bt = null;
        foreach (var kv in spawner.Roots)
        {
            if (kv.Value == null) continue;
            Vector3 sp = cam.WorldToScreenPoint(kv.Value.transform.position + Vector3.up);
            if (sp.z < 0) continue;
            float d = Vector2.Distance(new Vector2(sp.x, sp.y), (Vector2)Input.mousePosition);
            if (d < best) { best = d; bt = kv.Value.transform; }
        }
        return bt;
    }

    public string ModeLabel => mode == Mode.Overhead ? "OVERHEAD — the sky"
        : mode == Mode.Fly ? "FLY — invisible"
        : "FOLLOWING — " + (followTarget ? followTarget.name.Replace("Agent_", "") : "");
}
