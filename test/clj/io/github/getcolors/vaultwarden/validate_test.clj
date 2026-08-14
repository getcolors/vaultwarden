(ns io.github.getcolors.vaultwarden.validate-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [green.cli :as green-cli]
            [io.github.getcolors.vaultwarden.validate :as validate]))

(def fixture-file "test/fixtures/colors.yml")
(defn fixture [& {:as overrides}]
  (merge (green-cli/read-state fixture-file (slurp fixture-file)) overrides))
(defn matching [opts fragment]
  (filter #(str/includes? % fragment) (validate/state-errors opts)))

(deftest fixture-is-valid
  (is (= [] (validate/state-errors (fixture)))))

(deftest reports-all-invalid-fields
  (let [errs (validate/state-errors
              (fixture :vaultwarden-host "bad"
                       :vaultwarden-repo "bad"
                       :vaultwarden-owner-email "bad"
                       :vaultwarden-signups-allowed true
                       :vaultwarden-admin-enabled true
                       :litestream-retention "forever"))]
    (is (<= 6 (count errs)))
    (doseq [fragment ["host" "repo" "email" "signups" "admin" "retention"]]
      (is (some #(str/includes? % fragment) errs)))))

(deftest image-must-be-pinned
  (is (seq (matching (fixture :vaultwarden-image "ghcr.io/getcolors/vaultwarden")
                     "explicit tag"))))

(deftest profile-overlay-is-refused
  (is (= "COLORS_PAR_PROFILE" validate/profile-par))
  (is (seq (validate/env-errors {"COLORS_PAR_PROFILE" "other"})))
  (is (nil? (validate/env-errors {}))))

(deftest package-secrets-are-named
  (let [errs (str/join "\n" (validate/secret-errors (fixture)))]
    (doseq [par ["COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID"
                 "COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY"
                 "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN"]]
      (is (str/includes? errs par)))))
