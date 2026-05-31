// BuildScript — headless WebGL build so the world can be run/verified in a browser
// (no editor GUI needed). Run:
//   Unity -batchmode -projectPath <proj> -executeMethod BuildScript.BuildWebGL -quit
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class BuildScript
{
    public static void BuildWebGL()
    {
        // serve over a plain http server: disable compression, embed debug symbols
        PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        PlayerSettings.WebGL.exceptionSupport = WebGLExceptionSupport.FullWithStacktrace;
        PlayerSettings.runInBackground = true;
        EditorUserBuildSettings.development = true;

        var opts = new BuildPlayerOptions
        {
            scenes = new[] { "Assets/Scenes/Main.unity" },
            locationPathName = "Build/WebGL",
            target = BuildTarget.WebGL,
            options = BuildOptions.Development,
        };

        var report = BuildPipeline.BuildPlayer(opts);
        var s = report.summary;
        Debug.Log($"[Build] WebGL result={s.result} size={s.totalSize} time={s.totalTime} out={s.outputPath}");
        if (s.result != BuildResult.Succeeded)
            EditorApplication.Exit(1);
    }
}
