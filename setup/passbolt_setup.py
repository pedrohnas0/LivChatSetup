#!/usr/bin/env python3
"""
Módulo de setup do Passbolt (CE)
Segue o padrão dos módulos existentes (ex.: Chatwoot, N8N).
- Cria stack via Portainer com compose Jinja2
- Configura DNS via Cloudflare
- Usa MariaDB embarcado no compose
- Salva credenciais em /root/dados_vps/dados_passbolt
- Pós-deploy automatizado: gera chaves JWT, gera chave GPG do servidor,
  define fingerprint e cria o primeiro usuário admin.
"""

import subprocess
import os
import time
import re
from .base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.cloudflare_api import get_cloudflare_api


class PassboltSetup(BaseSetup):
    def __init__(self, network_name: str = None):
        super().__init__("Passbolt")
        self.portainer_api = PortainerAPI()
        self.network_name = network_name
        self.debug_log_path = None
        # Caminho centralizado para as credenciais do Passbolt
        self.credentials_path = "/root/dados_vps/dados_passbolt"

    # --- Utilidades locais ---
    def _is_docker_running(self) -> bool:
        try:
            result = subprocess.run(
                "docker info",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    # --- Pré-requisitos ---
    def validate_prerequisites(self) -> bool:
        if not self._is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
        return True

    # --- Coleta inputs ---
    def collect_user_inputs(self):
        print("\n=== Configuração do Passbolt ===")

        # Domínio Passbolt
        while True:
            domain = input("Digite o domínio para o Passbolt (ex: passbolt.seudominio.com): ").strip()
            if domain:
                break
            print("❌ Domínio é obrigatório!")

        # SMTP
        while True:
            smtp_email = input("Digite o Email para SMTP (ex: contato@seudominio.com): ").strip()
            if smtp_email:
                break
            print("❌ Email SMTP é obrigatório!")
        
        while True:
            smtp_user = input(f"Digite o Usuário para SMTP (ex: {smtp_email}): ").strip()
            if smtp_user:
                break
            print("❌ Usuário SMTP é obrigatório!")
        
        while True:
            smtp_password = input("Digite a Senha SMTP do Email: ").strip()
            if smtp_password:
                break
            print("❌ Senha SMTP é obrigatória!")
        
        while True:
            smtp_host = input("Digite o Host SMTP do Email (ex: smtp.hostinger.com): ").strip()
            if smtp_host:
                break
            print("❌ Host SMTP é obrigatório!")

        while True:
            smtp_port_str = input("Digite a porta SMTP do Email (ex: 465): ").strip()
            if smtp_port_str.isdigit():
                smtp_port = int(smtp_port_str)
                break
            print("❌ Porta deve ser um número!")

        smtp_tls = "true" if smtp_port == 465 else "false"

        # Admin inicial
        print("\n--- Usuário Admin Inicial ---")
        while True:
            admin_email = input("Email do Admin (usado no login): ").strip()
            if admin_email:
                break
            print("❌ Email do Admin é obrigatório!")
        while True:
            admin_first = input("Primeiro nome do Admin: ").strip()
            if admin_first:
                break
            print("❌ Primeiro nome é obrigatório!")
        while True:
            admin_last = input("Sobrenome do Admin: ").strip()
            if admin_last:
                break
            print("❌ Sobrenome é obrigatório!")

        # Email para a chave GPG do servidor (pode ser o mesmo do admin)
        server_key_email = input(
            "Email para a chave GPG do servidor (ENTER para usar o email do Admin): "
        ).strip() or admin_email

        # Confirmação
        print("\n=== Resumo ===")
        print(f"Domínio: {domain}")
        print(f"SMTP: {smtp_host}:{smtp_port} ({'TLS' if smtp_tls == 'true' else 'no TLS'})")
        print(f"Admin: {admin_first} {admin_last} <{admin_email}>")
        print(f"Email da chave GPG do servidor: {server_key_email}")
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm not in ["s", "sim", "y", "yes"]:
            return None

        return {
            "domain": domain,
            "smtp_email": smtp_email,
            "smtp_user": smtp_user,
            "smtp_password": smtp_password,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_tls": smtp_tls,
            "admin_email": admin_email,
            "admin_first": admin_first,
            "admin_last": admin_last,
            "server_key_email": server_key_email,
        }

    # --- DNS ---
    def setup_dns(self, domain: str) -> bool:
        self.logger.info("Configurando registros DNS via Cloudflare...")
        cf = get_cloudflare_api(self.logger)
        if not cf:
            self.logger.error("Falha ao inicializar Cloudflare API")
            return False
        return cf.setup_dns_for_service("Passbolt", [domain])

    # --- Execução principal ---
    def run(self) -> bool:
        if not self.validate_prerequisites():
            return False
        return self.install()

    def install(self) -> bool:
        try:
            # Prepara log de debug com timestamp
            try:
                os.makedirs("/root/dados_vps", exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                self.debug_log_path = f"/root/dados_vps/debug_passbolt_{ts}.log"
                with open(self.debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[INIT] Iniciando instalação do Passbolt em {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            except Exception as e:
                self.logger.warning(f"Não foi possível criar arquivo de log de debug: {e}")

            # Coleta dados do usuário
            variables = None
            while not variables:
                variables = self.collect_user_inputs()
                if not variables:
                    print("\nVamos tentar novamente...\n")

            # DNS (não bloqueante para avanço, mas registra warnings)
            if not self.setup_dns(variables["domain"]):
                self.logger.warning("Falha na configuração DNS, continuando...")

            # Configura credenciais do MariaDB embarcado
            db_name = "passbolt"
            db_user = "passbolt"
            db_password = self.portainer_api.generate_password(20, use_special_chars=False)

            # Variáveis para o template
            template_vars = {
                "network_name": self.network_name,
                "domain": variables["domain"],
                "db_name": db_name,
                "db_user": db_user,
                "db_password": db_password,
                "smtp_email": variables["smtp_email"],
                "smtp_user": variables["smtp_user"],
                "smtp_password": variables["smtp_password"],
                "smtp_host": variables["smtp_host"],
                "smtp_port": variables["smtp_port"],
                "smtp_tls": variables["smtp_tls"],
            }

            # Volumes declarados no compose
            volumes = [
                "passbolt_database",
                "passbolt_gpg",
                "passbolt_jwt",
            ]

            # Serviços para aguardar
            wait_services = ["passbolt_db", "passbolt_passbolt"]

            # Deploy via Portainer API
            success = self.portainer_api.deploy_service_complete(
                service_name="passbolt",
                template_path="docker-compose/passbolt.yaml.j2",
                template_vars=template_vars,
                volumes=volumes,
                wait_services=wait_services,
                credentials={
                    "domain": variables["domain"],
                    "db_name": db_name,
                    "db_user": db_user,
                    "db_password": db_password,
                    "smtp_email": variables["smtp_email"],
                    "smtp_user": variables["smtp_user"],
                    "smtp_host": variables["smtp_host"],
                    "smtp_port": variables["smtp_port"],
                    "smtp_tls": variables["smtp_tls"],
                    "admin_email": variables["admin_email"],
                    "admin_first": variables["admin_first"],
                    "admin_last": variables["admin_last"],
                    "server_key_email": variables["server_key_email"],
                },
            )

            if not success:
                self.logger.error("Falha na instalação do Passbolt")
                return False

            # Salva credenciais base do Passbolt no arquivo central antes do pós-setup
            try:
                os.makedirs("/root/dados_vps", exist_ok=True)
                with open(self.credentials_path, "w", encoding="utf-8") as f:
                    f.write(f"domain={variables['domain']}\n")
                    f.write(f"db_name={db_name}\n")
                    f.write(f"db_user={db_user}\n")
                    f.write(f"db_password={db_password}\n")
                    f.write(f"smtp_email={variables['smtp_email']}\n")
                    f.write(f"smtp_user={variables['smtp_user']}\n")
                    f.write(f"smtp_password={variables['smtp_password']}\n")
                    f.write(f"smtp_host={variables['smtp_host']}\n")
                    f.write(f"smtp_port={variables['smtp_port']}\n")
                    f.write(f"smtp_tls={variables['smtp_tls']}\n")
                self.logger.info(f"Credenciais base salvas em {self.credentials_path}")
            except Exception as e:
                self.logger.warning(f"Não foi possível salvar as credenciais base do Passbolt: {e}")

            # Pós-deploy: configurar JWT, GPG e criar admin
            if not self._post_deploy_setup(variables):
                self.logger.error("Pós-configuração do Passbolt falhou")
                return False

            self.logger.info("Instalação do Passbolt concluída com sucesso")
            self.logger.info(f"Acesse: https://{variables['domain']}")
            return True

        except Exception as e:
            self.logger.error(f"Erro durante instalação do Passbolt: {e}")
            return False

    # --- Pós-deploy: JWT, GPG, Admin ---
    def _get_container_id(self, name_filter: str) -> str:
        try:
            result = subprocess.run(
                f"docker ps -q --filter name={name_filter}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            cid = result.stdout.strip().splitlines()
            return cid[0] if cid else ""
        except Exception:
            return ""

    def _append_debug(self, text: str):
        try:
            if not self.debug_log_path:
                os.makedirs("/root/dados_vps", exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                self.debug_log_path = f"/root/dados_vps/debug_passbolt_{ts}.log"
            with open(self.debug_log_path, "a", encoding="utf-8") as f:
                f.write(text if text.endswith("\n") else text + "\n")
        except Exception:
            pass

    def _exec_in_container(self, cid: str, user: str, cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
        # Escapa aspas duplas no comando para evitar problemas de parsing
        escaped_cmd = cmd.replace('"', '\\"')
        full_cmd = f"docker exec -u {user} {cid} bash -lc \"{escaped_cmd}\""
        self._append_debug(f"[EXEC] user={user} cid={cid} cmd={cmd}")
        proc = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        self._append_debug(f"[EXIT] code={proc.returncode}")
        if proc.stdout:
            self._append_debug("[STDOUT]" + "\n" + proc.stdout)
        if proc.stderr:
            self._append_debug("[STDERR]" + "\n" + proc.stderr)
        return proc

    def _create_jwt_keys(self, cid: str) -> bool:
        self.logger.info("Gerando chaves JWT (ajustando permissões do diretório primeiro)...")
        # Garante que www-data consiga escrever no diretório de JWTs
        fix = self._exec_in_container(
            cid,
            "root",
            "chown -R www-data:www-data /etc/passbolt/jwt && chmod 750 /etc/passbolt/jwt",
        )
        if fix.returncode != 0:
            self.logger.warning(f"Não foi possível ajustar permissões do diretório JWT: {fix.stderr or fix.stdout}")
        proc = self._exec_in_container(
            cid,
            "www-data",
            "/usr/share/php/passbolt/bin/cake passbolt create_jwt_keys",
            timeout=180,
        )
        if proc.returncode != 0:
            self.logger.error(f"Falha ao criar JWT keys: {proc.stderr or proc.stdout}")
            return False
        # Após gerar, reforça as permissões conforme healthcheck recomenda (não gravável por www-data)
        post_fix = self._exec_in_container(
            cid,
            "root",
            "chown -R root:www-data /etc/passbolt/jwt && chmod 750 /etc/passbolt/jwt && chmod 640 /etc/passbolt/jwt/jwt.key /etc/passbolt/jwt/jwt.pem",
        )
        if post_fix.returncode != 0:
            self.logger.warning(f"Não foi possível reforçar permissões do diretório JWT: {post_fix.stderr or post_fix.stdout}")
        self.logger.info("Par de chaves JWT criado e permissões ajustadas.")
        return True

    def _healthcheck(self, cid: str, title: str = "") -> None:
        label = title or "Healthcheck"
        self.logger.info(f"Executando healthcheck ({label})...")
        proc = self._exec_in_container(cid, "www-data", "/usr/share/php/passbolt/bin/cake passbolt healthcheck", timeout=240)
        # Sempre logamos a saída completa no arquivo de debug
        out = proc.stdout + "\n" + proc.stderr
        self._append_debug(f"[HEALTHCHECK {label}]\n{out}")

    def _dump_env_info(self, cid: str) -> None:
        self.logger.info("Coletando informações de ambiente do container...")
        cmds = [
            "printenv | egrep 'APP_FULL_BASE_URL|EMAIL_|DATASOURCES_DEFAULT_|PASSBOLT_' || true",
            "ls -l /etc/passbolt || true",
            "ls -l /etc/passbolt/jwt || true",
            "ls -l /etc/passbolt/gpg || true",
            "test -f /etc/passbolt/passbolt.php && head -n 50 /etc/passbolt/passbolt.php || echo 'passbolt.php não presente, usando env'",
        ]
        for c in cmds:
            self._exec_in_container(cid, "root", c, timeout=60)

    def _generate_server_gpg(self, cid: str, email: str) -> str:
        self.logger.info("Gerando chave GPG do servidor...")
        batch = (
            "cat >/tmp/server-gpg-batch <<EOF\n"
            "Key-Type: RSA\nKey-Length: 3072\nSubkey-Type: RSA\nSubkey-Length: 3072\n"
            f"Name-Real: Passbolt Server\nName-Email: {email}\nExpire-Date: 0\n%no-protection\n%commit\n"
            "EOF"
        )
        # Cria batch e gera chave no keyring do www-data
        step1 = self._exec_in_container(cid, "root", batch)
        if step1.returncode != 0:
            self.logger.error(f"Falha ao preparar batch GPG: {step1.stderr}")
            return ""
        step2 = self._exec_in_container(cid, "www-data", "gpg --batch --gen-key /tmp/server-gpg-batch", timeout=300)
        if step2.returncode != 0:
            self.logger.error(f"Falha ao gerar chave GPG: {step2.stderr or step2.stdout}")
            return ""
        # Obtém fingerprint (mais robusto)
        get_fpr = self._exec_in_container(
            cid,
            "www-data",
            f"gpg --with-colons --list-keys '{email}' | grep '^fpr:' | head -n1 | cut -d: -f10",
        )
        fpr = get_fpr.stdout.strip()
        if not fpr:
            # Fallback: busca qualquer chave recém-criada
            self.logger.warning("Tentando obter fingerprint de qualquer chave recente...")
            get_fpr2 = self._exec_in_container(
                cid,
                "www-data",
                "gpg --with-colons --list-keys | grep '^fpr:' | tail -n1 | cut -d: -f10",
            )
            fpr = get_fpr2.stdout.strip()
            if not fpr:
                self.logger.error("Não foi possível obter o fingerprint da chave GPG")
                return ""
        # Assegura diretório e exporta chaves para /etc/passbolt/gpg
        export_cmd = (
            "mkdir -p /etc/passbolt/gpg && "
            "chown root:www-data /etc/passbolt/gpg && chmod 750 /etc/passbolt/gpg && "
            f"gpg --armor --export-secret-keys {fpr} > /etc/passbolt/gpg/serverkey_private.asc && "
            f"gpg --armor --export {fpr} > /etc/passbolt/gpg/serverkey.asc && "
            "chown root:www-data /etc/passbolt/gpg/serverkey_private.asc /etc/passbolt/gpg/serverkey.asc && "
            "chmod 640 /etc/passbolt/gpg/serverkey_private.asc /etc/passbolt/gpg/serverkey.asc"
        )
        exp = self._exec_in_container(cid, "root", export_cmd)
        if exp.returncode != 0:
            self.logger.error(f"Falha ao exportar chaves GPG: {exp.stderr or exp.stdout}")
            return ""
        return fpr

    def _update_service_env(self, service_name: str, env: dict) -> bool:
        self.logger.info("Atualizando variáveis de ambiente do serviço (reiniciará o container)...")
        parts = ["docker service update"]
        for k, v in env.items():
            parts.append(f"--env-add {k}={v}")
        parts.append(service_name)
        cmd = " ".join(parts)
        # Log detalhado
        self._append_debug(f"[SERVICE UPDATE] cmd={cmd}")
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        self._append_debug(f"[SERVICE UPDATE EXIT] code={proc.returncode}")
        if proc.stdout:
            self._append_debug("[SERVICE UPDATE STDOUT]\n" + proc.stdout)
        if proc.stderr:
            self._append_debug("[SERVICE UPDATE STDERR]\n" + proc.stderr)
        if proc.returncode != 0:
            self.logger.error(f"Falha ao atualizar env do serviço: {proc.stderr or proc.stdout}")
            return False
        return True

    def _register_admin(self, cid: str, email: str, first: str, last: str) -> str:
        self.logger.info("Registrando primeiro usuário admin (método oficial do docker)...")
        # Comando direto como www-data (método que funcionou manualmente)
        cmd_direct = (
            f"/usr/share/php/passbolt/bin/cake passbolt register_user "
            f"-u {email} -f '{first}' -l '{last}' -r admin"
        )
        proc = self._exec_in_container(cid, "www-data", cmd_direct, timeout=240)
        if proc.returncode != 0:
            # Fallback: usando su como root (método alternativo)
            self.logger.warning("Primeira tentativa falhou, tentando com su...")
            cmd_su = (
                f"su -m -c '/usr/share/php/passbolt/bin/cake passbolt register_user "
                f"-u {email} -f \"{first}\" -l \"{last}\" -r admin' -s /bin/sh www-data"
            )
            proc = self._exec_in_container(cid, "root", cmd_su, timeout=240)
            if proc.returncode != 0:
                self.logger.error(f"Falha ao registrar admin: {proc.stderr or proc.stdout}")
                return ""
        output = proc.stdout + "\n" + proc.stderr
        # Salva saída completa para facilitar debug posterior
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            dbg_path = f"/root/dados_vps/debug_passbolt_register_user_{ts}.log"
            with open(dbg_path, "w", encoding="utf-8") as f:
                f.write(output)
            self.logger.info(f"Saída do register_user salva em: {dbg_path}")
        except Exception as e:
            self.logger.warning(f"Não foi possível gravar log de debug do register_user: {e}")
        # Extrai link do setup: prioriza URLs contendo '/setup', senão pega a primeira URL absoluta
        match = re.search(r"https?://\S*/setup\S*", output)
        if match:
            link = match.group(0)
            self.logger.info(f"Link de instalação gerado: {link}")
            return link
        match_any = re.search(r"https?://\S+", output)
        if match_any:
            link = match_any.group(0)
            self.logger.info(f"URL detectada: {link}")
            return link
        # Tenta fallback com recover_user (caso o usuário já exista ou não retorne link)
        self.logger.warning("Link não detectado no register_user, tentando recover_user...")
        rec = self._exec_in_container(
            cid,
            "www-data",
            f"/usr/share/php/passbolt/bin/cake passbolt recover_user -u {email}",
            timeout=180,
        )
        out2 = rec.stdout + "\n" + rec.stderr
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            dbg_path2 = f"/root/dados_vps/debug_passbolt_recover_user_{ts}.log"
            with open(dbg_path2, "w", encoding="utf-8") as f:
                f.write(out2)
            self.logger.info(f"Saída do recover_user salva em: {dbg_path2}")
        except Exception:
            pass
        m2 = re.search(r"https?://\S*/setup\S*", out2)
        if m2:
            link = m2.group(0)
            self.logger.info(f"Link de instalação (recover_user): {link}")
            return link
        m2_any = re.search(r"https?://\S+", out2)
        if m2_any:
            link = m2_any.group(0)
            self.logger.info(f"URL detectada (recover_user): {link}")
            return link
        # fallback final: sem link, registra saída para análise
        self.logger.warning("Não foi possível detectar o link automaticamente após register_user e recover_user.")
        self.logger.debug(f"Saída completa register_user: {output}")
        self.logger.debug(f"Saída completa recover_user: {out2}")
        return ""

    def _post_deploy_setup(self, variables: dict) -> bool:
        # Obtém container do app
        cid = self._get_container_id("passbolt_passbolt")
        if not cid:
            self.logger.error("Container do Passbolt não encontrado para pós-configuração")
            return False

        # Dump de informações úteis para debug
        self._dump_env_info(cid)
        # Healthcheck inicial
        self._healthcheck(cid, title="inicial")

        # 1) Criar chaves JWT (necessário para o fluxo de registro)
        if not self._create_jwt_keys(cid):
            self.logger.error("Falha ao gerar chaves JWT")
            return False
        # Healthcheck após JWT
        self._healthcheck(cid, title="após JWT")

        # 2) Gerar chave GPG do servidor e aplicar envs
        fpr = self._generate_server_gpg(cid, variables["server_key_email"])
        if not fpr:
            self.logger.error("Falha ao gerar/importar chave GPG do servidor")
        else:
            ok_env = self._update_service_env(
                "passbolt_passbolt",
                {
                    "PASSBOLT_GPG_SERVER_KEY_FINGERPRINT": fpr,
                    "PASSBOLT_KEY_EMAIL": variables["server_key_email"],
                    "PASSBOLT_SSL_FORCE": "true",
                },
            )
            if not ok_env:
                self.logger.error("Falha ao atualizar env do serviço passbolt_passbolt")
            else:
                # Aguardar reinício do serviço
                self.logger.info("Aguardando serviço reiniciar após atualização de env...")
                if not self.portainer_api.wait_for_service("passbolt_passbolt", timeout=420):
                    self.logger.error("Serviço não ficou pronto após atualização de env")
                else:
                    # Re-obter CID e healthcheck
                    cid_new = self._get_container_id("passbolt_passbolt") or cid
                    cid = cid_new
                    self._healthcheck(cid, title="após GPG/env")

        # 3) Registrar admin e obter link de instalação (com retry simples)
        setup_link = self._register_admin(
            cid,
            variables["admin_email"],
            variables["admin_first"],
            variables["admin_last"],
        )
        if not setup_link:
            self.logger.warning("Primeira tentativa de obter link falhou. Aguardando 5s e tentando novamente...")
            time.sleep(5)
            setup_link = self._register_admin(
                cid,
                variables["admin_email"],
                variables["admin_first"],
                variables["admin_last"],
            )

        # Salvar info adicionais nas credenciais
        creds_extra = {
            "admin_email": variables["admin_email"],
            "admin_first": variables["admin_first"],
            "admin_last": variables["admin_last"],
        }
        # Garante que o fingerprint seja salvo corretamente
        if fpr and fpr != "0":
            creds_extra["gpg_fingerprint"] = fpr
        else:
            self.logger.warning("GPG fingerprint não foi obtido corretamente")
        if setup_link:
            creds_extra["setup_link"] = setup_link
            self.logger.info(f"Finalize o cadastro acessando: {setup_link}")
        else:
            self.logger.warning("Nenhum link de instalação detectado automaticamente. Verifique os logs de debug em /root/dados_vps/.")

        # Faz um append seguro ao arquivo de credenciais do serviço
        try:
            with open(self.credentials_path, "a", encoding="utf-8") as f:
                for k, v in creds_extra.items():
                    f.write(f"{k}={v}\n")
        except Exception as e:
            self.logger.warning(f"Não foi possível salvar informações adicionais de credenciais: {e}")

        return True
