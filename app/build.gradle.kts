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
        versionCode = 2
        versionName = "1.1"
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
        create("job") {
            dimension = "app"
            applicationIdSuffix = ".job"
            resValue("string", "app_name", "Fréquence Job")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/PAQr6g8JgByjY77QQb91Gn\"")
        }
        create("revision") {
            dimension = "app"
            applicationIdSuffix = ".revision"
            resValue("string", "app_name", "Fréquence Révision")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/MjY7UqNP5GabVxX82qde9D\"")
        }
        create("trail") {
            dimension = "app"
            applicationIdSuffix = ".trail"
            resValue("string", "app_name", "Fréquence Trail")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/FfSfL6RSuqUadWgrxk7PKD\"")
        }
        // Famille « Coda » : les apps d'apprentissage des langages.
        create("rouille") {
            dimension = "app"
            applicationIdSuffix = ".rouille"
            resValue("string", "app_name", "Coda Rouille")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/Y2BTeqDKqqsgdtHh3scWnh\"")
        }
        create("bitabit") {
            dimension = "app"
            applicationIdSuffix = ".bitabit"
            resValue("string", "app_name", "Coda++")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/1YwUss69142sy7uszzByYJ\"")
        }
        create("dodiese") {
            dimension = "app"
            applicationIdSuffix = ".dodiese"
            resValue("string", "app_name", "Coda Dièse")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/RogiUTnurBKvh7bQ9noy8z\"")
        }
        create("miseenprod") {
            dimension = "app"
            applicationIdSuffix = ".miseenprod"
            resValue("string", "app_name", "Mise en prod")
            buildConfigField("String", "START_URL", "\"https://claude.ai/artifact/QA3p3jZwAJe8jaXWK2xSrf\"")
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
