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

(deftest official-image-needs-no-github-credential
  (let [env (assoc package-secrets "COLORS_PAR_NO_INFRA_SMTP_PASSWORD" "x" "COLORS_PAR_DO_TOKEN" "x")
        opts (assoc (dissoc (fixture) :vaultwarden-repo) :green/event :create)
        result (workflow/start-step opts env)]
    (is (= 0 (:green/exit result)))
    (is (not (str/includes? (str (:green/err result)) "COLORS_PAR_GITHUB_TOKEN")))))

(deftest delete-is-protected
  (let [result (workflow/start-step (assoc (fixture) :green/event :delete) {})]
    (is (= 2 (:green/exit result)))
    (is (str/includes? (:green/err result) "COMPUTE_PREVENT_DESTROY"))))

(deftest graph-reuses-once-stages-and-reverses-on-delete
  (is (= [:vaultwarden/compute]
         (vec (rest (workflow/wire-fn :vaultwarden/start {:green/event :create})))))
  (is (= [:vaultwarden/github]
         (vec (rest (workflow/wire-fn :vaultwarden/start
                                      (assoc (fixture) :green/event :delete))))))
  (is (= [:vaultwarden/smtp :vaultwarden/compute]
         (vec (rest (workflow/wire-fn :vaultwarden/dns {:green/event :delete}))))))

(deftest official-image-omits-github-from-the-graph
  (let [opts (dissoc (fixture) :vaultwarden-repo)]
    (is (= []
           (vec (rest (workflow/wire-fn :vaultwarden/ansible-remote
                                        (assoc opts :green/event :create))))))
    (is (= [:vaultwarden/ansible-cleanup]
           (vec (rest (workflow/wire-fn :vaultwarden/start
                                        (assoc opts :green/event :delete))))))))

(require '[io.github.getcolors.vaultwarden.machine :as machine]
         '[io.github.getcolors.vaultwarden.tools :as tools]
         '[io.github.getcolors.compute-inspection :as inspection]
         '[green.ansible :as ansible])

(deftest direct-compute-contract
  (is (= [machine/step :vaultwarden/smtp] (workflow/wire-fn :vaultwarden/compute {:green/event :create})))
  (is (= ["vaultwarden-fixture/tofu-compute.tfstate"] (:legacy_state_keys (machine/requirements (fixture)))))
  (is (seq (machine/errors (assoc (fixture) :provider-compute "no-infra"))))
  (is (seq (machine/errors (assoc (fixture) :compute-http-sources [])))))

(deftest recorded-inventory-fails-closed
  (with-redefs [inspection/read-deployment (fn [opts env]
                                           (is (= {"AWS_PROFILE" "fixture"} env))
                                           {:status "absent"})]
    (is (= 1 (:green/exit (machine/load-inventory (assoc (fixture) :ip "203.0.113.99") {"AWS_PROFILE" "fixture"}))))))

(deftest ssh-uses-recorded-node-and-profile
  (with-redefs [ansible/ansible-with-spec
                (fn [opts config specs]
                  (is (= [{:name "vaultwarden-fixture" :ip "203.0.113.8" :user "ubuntu" :identity_file "/tmp/external"}]
                         (get-in config [:extra-vars :ssh_hosts])))
                  (is (= "absent" (get-in config [:extra-vars :block_state]))) opts)]
    (tools/ansible-local-step (assoc (fixture) :green/event :delete :once/compute-params
                                    {:name "cloud-label" :ip "203.0.113.8" :user "ubuntu" :ssh-private-key-path "/tmp/external"}))))
