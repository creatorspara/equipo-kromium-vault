#!/usr/bin/env python3
"""
patch_android.py
Configures Flutter Android build files for Equipo Kromium Vault:
- Ensures compileSdk is set to 36 across main app and all plugin subprojects.
- Injects Android permissions and application label in AndroidManifest.xml.
"""
import os
import re
import sys

def patch_app_build_gradle():
    app_kts = os.path.join("android", "app", "build.gradle.kts")
    app_groovy = os.path.join("android", "app", "build.gradle")
    
    target = app_kts if os.path.exists(app_kts) else (app_groovy if os.path.exists(app_groovy) else None)
    if not target:
        print("[WARN] Neither android/app/build.gradle.kts nor build.gradle found.")
        return
        
    with open(target, "r", encoding="utf-8") as f:
        content = f.read()
        
    content = re.sub(r'compileSdk\s*=\s*.*', 'compileSdk = 36', content)
    content = re.sub(r'compileSdkVersion\s+.*', 'compileSdkVersion 36', content)
    content = re.sub(r'targetSdk\s*=\s*.*', 'targetSdk = 35', content)
    content = re.sub(r'targetSdkVersion\s+.*', 'targetSdkVersion 35', content)
    
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Patched {target} with compileSdk = 36")

def patch_root_build_gradle():
    root_kts = os.path.join("android", "build.gradle.kts")
    root_groovy = os.path.join("android", "build.gradle")
    
    target = root_kts if os.path.exists(root_kts) else (root_groovy if os.path.exists(root_groovy) else None)
    if not target:
        print("[WARN] Neither android/build.gradle.kts nor build.gradle found.")
        return
        
    with open(target, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "setCompileSdkVersion" in content or "compileSdkVersion" in content and "subprojects" in content:
        # Check if subprojects compileSdk alignment is already present
        if "compileSdk" in content and "36" in content:
            print(f"[INFO] {target} already contains compileSdk 36 configuration.")
            return

    if target.endswith(".kts"):
        patch = """
// Equipo Kromium: Force compileSdk 36 across all subproject plugins
subprojects {
    if (project.name == "app") return@subprojects
    val configureProject: () -> Unit = {
        val androidExt = project.extensions.findByName("android")
        if (androidExt != null) {
            try {
                val m = androidExt.javaClass.getMethod("setCompileSdkVersion", java.lang.Integer.TYPE)
                m.invoke(androidExt, 36)
            } catch (e1: Exception) {
                try {
                    val m2 = androidExt.javaClass.getMethod("compileSdkVersion", java.lang.Integer.TYPE)
                    m2.invoke(androidExt, 36)
                } catch (e2: Exception) {
                    try {
                        val m3 = androidExt.javaClass.getMethod("setCompileSdk", java.lang.Integer::class.java)
                        m3.invoke(androidExt, 36)
                    } catch (e3: Exception) {}
                }
            }
        }
    }

    if (project.state.executed) {
        configureProject()
    } else {
        project.afterEvaluate {
            configureProject()
        }
    }
}
"""
    else:
        patch = """
// Equipo Kromium: Force compileSdk 36 across all subproject plugins
subprojects { project ->
    if (project.name == "app") return
    def configureAndroid = {
        if (project.hasProperty("android")) {
            try {
                project.android.compileSdkVersion = 36
            } catch (Exception ignored) {}
        }
    }
    if (project.state.executed) {
        configureAndroid()
    } else {
        project.afterEvaluate {
            configureAndroid()
        }
    }
}
"""
    with open(target, "a", encoding="utf-8") as f:
        f.write("\n" + patch + "\n")
    print(f"[OK] Appended subproject compileSdk 36 injection to {target}")

def patch_manifest():
    manifest_path = os.path.join("android", "app", "src", "main", "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        print(f"[WARN] Manifest not found at {manifest_path}")
        return
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "android.permission.READ_EXTERNAL_STORAGE" not in content:
        permissions = (
            '    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />\n'
            '    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />\n'
            '    <application'
        )
        content = content.replace("<application", permissions, 1)
        
    content = re.sub(r'android:label="[^"]*"', 'android:label="Equipo Kromium Vault"', content)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Patched {manifest_path} with permissions and app label.")

if __name__ == "__main__":
    patch_app_build_gradle()
    patch_root_build_gradle()
    patch_manifest()
    print("[SUCCESS] Android environment configuration completed.")
