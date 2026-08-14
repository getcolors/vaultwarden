(ns io.github.getcolors.vaultwarden.workflow-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [io.github.getcolors.vaultwarden.validate-test :refer [fixture]]
            [io.github.getcolors.vaultwarden.workflow :as workflow]))

(def package-secrets
  {"COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID" "x"
   "COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY" "x"
   "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN" "x"})

(deftest build-and-dry-run-need-no-credentials
  (is (= 0 (:green/exit (workflow/start-step (assoc (fixture) :green/event :build) {}))))
  (is (= 0 (:green/exit (workflow/start-step
                         (assoc (fixture) :green/event :create :green/dry-run true) {})))))

(deftest real-create-demands-package-and-provider-credentials
  (let [result (workflow/start-step (assoc (fixture) :green/event :create) {})]
    (is (= 2 (:green/exit result)))
    (is (str/includes? (:green/err result) "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN")))
  (let [result (workflow/start-step (assoc (fixture) :green/event :create) package-secrets)]
    (is (= 2 (:green/exit result)))
    (is (str/includes? (:green/err result) "COLORS_PAR_NO_INFRA_SMTP_PASSWORD"))))

(deftest delete-is-protected
  (let [result (workflow/start-step (assoc (fixture) :green/event :delete) {})]
    (is (= 2 (:green/exit result)))
    (is (str/includes? (:green/err result) "COMPUTE_PREVENT_DESTROY"))))

(deftest graph-reuses-once-stages-and-reverses-on-delete
  (is (= [:vaultwarden/compute :vaultwarden/smtp]
         (vec (rest (workflow/wire-fn :vaultwarden/start {:green/event :create})))))
  (is (= [:vaultwarden/github]
         (vec (rest (workflow/wire-fn :vaultwarden/start {:green/event :delete})))))
  (is (= [:vaultwarden/smtp :vaultwarden/compute]
         (vec (rest (workflow/wire-fn :vaultwarden/dns {:green/event :delete}))))))
