plugins {
    id("com.android.application")
}

android {
    namespace = "fr.frequence.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "fr.frequence"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    // Même clé à chaque compilation : une nouvelle version s'installe par-dessus l'ancienne.
    signingConfigs {
        create("perso") {
            storeFile = file("frequence.keystore")
            storePassword = "frequence"
            keyAlias = "frequence"
            keyPassword = "frequence"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("perso")
        }
    }

    // Une « saveur » par app : nom, lien et icône propres, installables côte à côte.
    flavorDimensions += "app"
    productFlavors {
        create("matin") {
            dimension = "app"
            applicationIdSuffix = ".matin"
            resValue("string", "app_name", "Fréquence Matin")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/91RN5RAJ1kdwvfUWYXf9SW\"")
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
