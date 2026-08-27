(ns io.github.getcolors.vaultwarden.tools-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [io.github.getcolors.vaultwarden.tools :as tools]
            [io.github.getcolors.vaultwarden.validate-test :refer [fixture]]))

(deftest adapter-builds-one-once-application
  (let [opts (tools/with-once-shape (fixture))
        app (get-in opts [:once :applications 0])
        env (str/join "\n" (:env app))]
    (is (= "vault.example.com" (:host app)))
    (is (= "ghcr.io/getcolors/vaultwarden:1.0.0" (:image app)))
    (is (= "getcolors/vaultwarden" (:github app)))
    (is (str/includes? env "DOMAIN=https://vault.example.com"))
    (is (str/includes? env "SIGNUPS_ALLOWED=false"))
    (is (str/includes? env "COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID"))
    (is (str/includes? env "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN"))
    (is (not (str/includes? env "secret-value")))))

(deftest adapter-omits-github-for-the-public-image
  (let [app (get-in (tools/with-once-shape (dissoc (fixture) :vaultwarden-repo))
                    [:once :applications 0])]
    (is (= "ghcr.io/getcolors/vaultwarden:1.0.0" (:image app)))
    (is (not (contains? app :github)))))

(deftest once-storage-path-is-fixed
  (is (some #{"DATA_FOLDER=/storage"} (tools/app-env (fixture)))))
