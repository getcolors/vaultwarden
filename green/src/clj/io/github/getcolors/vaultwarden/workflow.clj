(ns io.github.getcolors.vaultwarden.workflow
  (:require [green.cli :as green-cli]
            [green.dry-run :as dry-run]
            [green.lifecycle :as lifecycle]
            [green.progress :as progress]
            [green.tofu :as tofu]
            [green.workflow :as wf]
            [io.github.getcolors.once.github :as once-github]
            [io.github.getcolors.once.tools :as once-tools]
            [io.github.getcolors.once.workflow :as once-workflow]
            [io.github.getcolors.vaultwarden.tools :as tools]
            [io.github.getcolors.vaultwarden.validate :as validate]))

(def defaults
  {:compute-prevent-destroy true
   :provider-compute "digitalocean"
   :provider-dns "cloudflare"
   :provider-smtp "resend"
   :provider-backend "local"
   :workdir ".colors"})

(defn start-step
  ([opts] (start-step opts (System/getenv)))
  ([opts env]
   (let [checked
         (lifecycle/preflight
          opts {:defaults defaults
                :overlay green-cli/read-pars
                :validators
                [(fn [_ env _] (validate/env-errors env))
                 (fn [opts _ _] (validate/state-errors opts))
                 (fn [opts _ {:keys [event real?]}]
                   (when (and real? (= :create event))
                     (validate/secret-errors opts)))]}
          env)]
     (if (wf/failed? checked)
       checked
       (once-workflow/start-step (tools/with-once-shape checked) env)))))

(defn ansible-cleanup-step [opts]
  (-> opts once-tools/ansible-local-step once-tools/ansible-remote-step))

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
      :vaultwarden/dns [once-tools/tofu-dns-step :vaultwarden/smtp :vaultwarden/compute]
      :vaultwarden/smtp [once-tools/tofu-smtp-step]
        :vaultwarden/compute [once-tools/tofu-compute-step])
      (case step
        :vaultwarden/start [start-step :vaultwarden/compute :vaultwarden/smtp]
        :vaultwarden/compute [once-tools/tofu-compute-step :vaultwarden/dns]
        :vaultwarden/smtp [once-tools/tofu-smtp-step :vaultwarden/dns]
        :vaultwarden/dns [once-tools/tofu-dns-step :vaultwarden/smtp-post]
        :vaultwarden/smtp-post [once-tools/tofu-smtp-post-step
                                :vaultwarden/ansible-local :vaultwarden/ansible-remote]
        :vaultwarden/ansible-local [once-tools/ansible-local-step]
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
  (-> (wf/workflow {:start :vaultwarden/start :wire-fn wire-fn})
      (wf/advice-add :vaultwarden/compute :before ::backend (backend-advice tools/compute-tool))
      (wf/advice-add :vaultwarden/smtp :before ::backend (backend-advice tools/smtp-tool))
      (wf/advice-add :vaultwarden/dns :before ::backend (backend-advice tools/dns-tool))
      (wf/advice-add :vaultwarden/smtp-post :before ::backend (backend-advice tools/smtp-post-tool))
      progress/advise
      (dry-run/advise side-effecting-steps)))
