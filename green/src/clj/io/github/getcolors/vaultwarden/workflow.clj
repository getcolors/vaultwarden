(ns io.github.getcolors.vaultwarden.workflow
  (:require [clojure.java.io :as io]
            [clojure.walk :as walk]
            [green.cli :as green-cli]
            [green.dry-run :as dry-run]
            [green.lifecycle :as lifecycle]
            [green.progress :as progress]
            [green.tofu :as tofu]
            [green.workflow :as wf]
            [io.github.getcolors.once.github :as once-github]
            [io.github.getcolors.once.tools :as once-tools]
            [io.github.getcolors.vaultwarden.machine :as machine]
            [io.github.getcolors.vaultwarden.tools :as tools]
            [io.github.getcolors.vaultwarden.validate :as validate]))

(def defaults
  {:compute-prevent-destroy true
   :provider-compute "digitalocean"
   :provider-dns "cloudflare"
   :provider-smtp "resend"
   :provider-backend "r2"
   :workdir ".colors"})

(defn- state-output
  "Read a previously applied stage's `params` output, or nil when the stage has
  no state yet."
  [opts tool]
  (try
    (some-> (tofu/outputs (tools/tool-dir opts tool)
                          (tools/backend-credential-env opts))
            :params walk/keywordize-keys)
    (catch Exception _ nil)))

(defn- adopt-existing-state
  "Delete renders the same templates as create, so a destroy needs the params
  earlier stages produced (compute ip, smtp domain id and records)."
  [opts]
  (let [loaded (machine/load-inventory opts)]
    (if (or (wf/failed? loaded) (:colors-compute/already-destroyed loaded)) loaded
        (let [smtp (state-output opts "tofu-smtp")]
          (cond-> loaded smtp (-> (merge smtp) (assoc :once/smtp-params smtp)))))))

(defn- with-deploy-keys
  "Attach the keys `ansible-remote` installs and the `github` step publishes.

  Generating them is a create-time side effect, so a build or a dry-run takes
  fixed placeholders instead: a fresh key rendered into the artifact would make
  the build nondeterministic and break byte parity between the colours."
  [opts real?]
  (if (and real? (= :create (:green/event opts)))
    (let [[keys err] (once-github/generate-keys opts)]
      (if err
        (assoc opts :green/exit 1 :green/err err)
        (assoc opts
               :green/exit 0
               :once/deploy-keys keys
               :once/key-dir (some-> (first keys) :private-file io/file .getParent))))
    (assoc opts :green/exit 0 :once/deploy-keys (once-github/placeholder-keys opts))))

(defn start-step
  ([opts] (start-step opts (System/getenv)))
  ([opts env]
   (lifecycle/preflight opts
    {:defaults defaults :overlay green-cli/read-pars
     :validators
     [(fn [_ e _] (validate/env-errors e))
      (fn [o _ _] (concat (validate/state-errors o) (validate/integration-errors o)))
      (fn [o _ {:keys [event real?]}] (when (and real? (#{:create :delete} event)) (validate/credential-errors o)))
      (fn [o _ {:keys [event real?]}] (when (and real? (= :create event)) (validate/secret-errors o)))
      (fn [o _ {:keys [event real?]}]
        (when (and real? (= :delete event) (:compute-prevent-destroy o))
          [(str "compute destruction is protected; set " (green-cli/par-name :compute-prevent-destroy) "=false to delete")]))]
     :after-validate
     (fn [o _ {:keys [event real?]}]
       (let [o (tools/with-once-shape o)]
         (if (and real? (= :delete event)) (adopt-existing-state o) (with-deploy-keys o real?))))}
    env)))

(defn ansible-cleanup-step [opts]
  (let [result (tools/ansible-local-step opts)]
    (if (wf/failed? result) result (once-tools/ansible-remote-step result))))

(defn wire-fn [step run-opts]
  (let [github? (some? (:vaultwarden-repo run-opts))]
    (if (= :delete (:green/event run-opts))
      (case step
        :vaultwarden/start (if github?
                             [start-step :vaultwarden/github]
                             [start-step :vaultwarden/ansible-cleanup])
      :vaultwarden/github [once-github/github-step :vaultwarden/ansible-cleanup]
      :vaultwarden/ansible-cleanup [ansible-cleanup-step :vaultwarden/smtp-post]
      :vaultwarden/smtp-post [once-tools/tofu-smtp-post-step :vaultwarden/dns]
      :vaultwarden/dns [once-tools/tofu-dns-step :vaultwarden/smtp]
      :vaultwarden/smtp [once-tools/tofu-smtp-step :vaultwarden/compute]
        :vaultwarden/compute [machine/step])
      (case step
        :vaultwarden/start [start-step :vaultwarden/compute]
        :vaultwarden/compute [machine/step :vaultwarden/smtp]
        :vaultwarden/smtp [once-tools/tofu-smtp-step :vaultwarden/dns]
        :vaultwarden/dns [once-tools/tofu-dns-step :vaultwarden/smtp-post]
        :vaultwarden/smtp-post [once-tools/tofu-smtp-post-step
                                :vaultwarden/ansible-local]
        :vaultwarden/ansible-local [tools/ansible-local-step :vaultwarden/ansible-remote]
        :vaultwarden/ansible-remote (if github?
                                      [once-tools/ansible-remote-step :vaultwarden/github]
                                      [once-tools/ansible-remote-step])
        :vaultwarden/github [once-github/github-step]))))

(defn backend-advice [tool]
  (tofu/conventional-backend-advice
   {:dir-fn #(tools/tool-dir % tool)
    :key-fn #(str (or (:profile %) "vaultwarden") "/" tool ".tfstate")}))

(def side-effecting-steps
  [:vaultwarden/compute :vaultwarden/smtp :vaultwarden/dns
   :vaultwarden/smtp-post :vaultwarden/ansible-local
   :vaultwarden/ansible-remote :vaultwarden/ansible-cleanup
   :vaultwarden/github])

(def workflow
  (-> (wf/workflow {:start :vaultwarden/start :wire-fn wire-fn :next-fn (fn [step successors opts] (if (or (wf/failed? opts) (and (= step :vaultwarden/start) (= :delete (:green/event opts)) (:colors-compute/already-destroyed opts))) [] (mapv #(vector % opts) successors)))})
      (wf/advice-add :vaultwarden/smtp :before ::backend (backend-advice tools/smtp-tool))
      (wf/advice-add :vaultwarden/dns :before ::backend (backend-advice tools/dns-tool))
      (wf/advice-add :vaultwarden/smtp-post :before ::backend (backend-advice tools/smtp-post-tool))
      progress/advise
      (dry-run/advise side-effecting-steps)))
