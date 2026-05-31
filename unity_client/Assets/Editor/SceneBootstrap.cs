// SceneBootstrap — builds the Phase-1 scene from code so no GUI is needed.
// Run headless: Unity -batchmode -projectPath <proj> -executeMethod SceneBootstrap.Build -quit
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class SceneBootstrap
{
    public static void Build()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // World controller: the Convex bridge + the cube spawner
        var world = new GameObject("World");
        world.AddComponent<ConvexWorldClient>();
        world.AddComponent<AgentSpawner>();

        // a reference ground plane under the agents
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.position = new Vector3(25f, 0f, -25f);
        ground.transform.localScale = new Vector3(8f, 1f, 8f);

        // overhead camera looking down at the map (tweak once we see real positions)
        var cam = Camera.main;
        if (cam != null)
        {
            cam.transform.position = new Vector3(25f, 38f, -58f);
            cam.transform.rotation = Quaternion.Euler(42f, 0f, 0f);
            cam.farClipPlane = 600f;
            cam.backgroundColor = new Color(0.07f, 0.08f, 0.10f);
        }

        System.IO.Directory.CreateDirectory(Application.dataPath + "/Scenes");
        bool ok = EditorSceneManager.SaveScene(scene, "Assets/Scenes/Main.unity");

        // make Main the scene that opens / builds
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Scenes/Main.unity", true) };

        Debug.Log("[Bootstrap] Main.unity " + (ok ? "saved" : "FAILED") +
                  " with World(ConvexWorldClient+AgentSpawner), Ground, Camera.");
    }
}
