const { withAppBuildGradle } = require("@expo/config-plugins");

/**
 * expo prebuild always signs the "release" build type with the debug key unless
 * customized. CI decodes a real release keystore into android/app/release.keystore
 * and passes its credentials via env vars; this plugin wires that into build.gradle
 * so `gradlew assembleRelease` produces a properly, consistently signed APK across
 * every CI run (a stable signing identity is required for future builds to install
 * as updates over an existing install rather than needing an uninstall each time).
 */
module.exports = function withReleaseSigning(config) {
  return withAppBuildGradle(config, (config) => {
    let contents = config.modResults.contents;

    if (!contents.includes("signingConfigs.release")) {
      contents = contents.replace(
        "signingConfigs {",
        `signingConfigs {
        release {
            storeFile file(System.getenv("ANDROID_RELEASE_KEYSTORE_PATH") ?: "release.keystore")
            storePassword System.getenv("ANDROID_RELEASE_KEYSTORE_PASSWORD") ?: ""
            keyAlias System.getenv("ANDROID_RELEASE_KEY_ALIAS") ?: ""
            keyPassword System.getenv("ANDROID_RELEASE_KEYSTORE_PASSWORD") ?: ""
        }`
      );

      const buildTypesIdx = contents.indexOf("buildTypes {");
      const releaseIdx = buildTypesIdx !== -1 ? contents.indexOf("release {", buildTypesIdx) : -1;
      if (releaseIdx !== -1) {
        const before = contents.slice(0, releaseIdx);
        const after = contents.slice(releaseIdx).replace("signingConfigs.debug", "signingConfigs.release");
        contents = before + after;
      }

      config.modResults.contents = contents;
    }

    return config;
  });
};
