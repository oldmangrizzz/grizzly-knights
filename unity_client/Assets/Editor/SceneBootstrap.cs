// SceneBootstrap — builds the scene from code (no GUI). Run:
//   Unity -batchmode -projectPath <proj> -executeMethod SceneBootstrap.Build -quit
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class SceneBootstrap
{
    public static void Build()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        var world = new GameObject("World");
        world.AddComponent<ConvexWorldClient>();
        world.AddComponent<AgentSpawner>();

        // ground centered under the agent cluster, dark so characters read
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.position = new Vector3(45f, 0f, -45f);
        ground.transform.localScale = new Vector3(14f, 1f, 14f);
        var gmat = new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard"));
        var dark = new Color(0.11f, 0.12f, 0.14f);
        if (gmat.HasProperty("_BaseColor")) gmat.SetColor("_BaseColor", dark); else gmat.color = dark;
        if (gmat.HasProperty("_Smoothness")) gmat.SetFloat("_Smoothness", 0.1f);
        ground.GetComponent<Renderer>().sharedMaterial = gmat;

        // low 3/4 camera framing the crowd
        var cam = Camera.main;
        if (cam != null)
        {
            cam.transform.position = new Vector3(45f, 90f, -40f);
            cam.transform.rotation = Quaternion.Euler(82f, 0f, 0f);
            cam.farClipPlane = 1200f;
            cam.backgroundColor = new Color(0.05f, 0.06f, 0.09f);
            cam.gameObject.AddComponent<WatcherCamera>();   // overhead/fly/follow rig
        }

        // lighting: warm key + lifted ambient so faces aren't black
        var lightGo = GameObject.Find("Directional Light");
        if (lightGo)
        {
            var L = lightGo.GetComponent<Light>();
            L.intensity = 1.15f;
            L.color = new Color(1f, 0.96f, 0.9f);
            lightGo.transform.rotation = Quaternion.Euler(48f, -32f, 0f);
        }
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.32f, 0.34f, 0.40f);

        System.IO.Directory.CreateDirectory(Application.dataPath + "/Scenes");
        bool ok = EditorSceneManager.SaveScene(scene, "Assets/Scenes/Main.unity");
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Scenes/Main.unity", true) };
        Debug.Log("[Bootstrap] Main.unity " + (ok ? "saved" : "FAILED"));
    }
}
