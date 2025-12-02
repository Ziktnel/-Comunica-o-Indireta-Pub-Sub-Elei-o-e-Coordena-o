import paho.mqtt.client as mqtt
import json
import random
import threading
import time
import hashlib
import sys

BROKER = "broker.emqx.io"
PORT = 1883

TOPIC_INIT = "sd/init"
TOPIC_VOTE = "sd/voting"
TOPIC_NEW_TASK = "sd/challenge"
TOPIC_SUBMIT = "sd/solution"
TOPIC_FEEDBACK = "sd/result"


class DistributedNode:
    """
    Implementação reescrita do nó distribuído.
    Estrutura totalmente nova, mantendo a mesma funcionalidade.
    """

    def __init__(self, total_nodes):
        self.total_nodes = int(total_nodes)

        # IDs gerados aleatoriamente
        self.node_id = random.randint(0, 65535)
        self.vote_number = random.randint(0, 65535)

        # Estados e tabelas internas
        self.phase = "DISCOVERY"
        self.peers = set()
        self.received_votes = {}

        # Controle de mineração
        self.transaction_id = 0
        self.difficulty = 0
        self.is_leader = False
        self.allow_mining = False
        self.transaction_closed = False

        # MQTT setup
        self.client = mqtt.Client(client_id=str(self.node_id))
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # ===============================
    #  MQTT HANDLERS
    # ===============================

    def on_connect(self, client, userdata, flags, rc):
        print(f"[{self.node_id}] Conexão estabelecida com sucesso!")

        # Inscreve em todos os tópicos relevantes
        client.subscribe([
            (TOPIC_INIT, 0),
            (TOPIC_VOTE, 0),
            (TOPIC_NEW_TASK, 0),
            (TOPIC_SUBMIT, 0),
            (TOPIC_FEEDBACK, 0)
        ])

        # Inicia processo de descoberta
        threading.Thread(target=self.discovery_loop, daemon=True).start()

    # ===============================
    #  PROCESSAMENTO DE MENSAGENS
    # ===============================

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except:
            return

        topic = msg.topic

        # ------------------------------
        # 1) Fase de descoberta
        # ------------------------------
        if topic == TOPIC_INIT and self.phase == "DISCOVERY":
            sender = data["ClientID"]

            if sender not in self.peers:
                self.peers.add(sender)
                print(f"[{self.node_id}] Detectado participante {sender} - {len(self.peers)}/{self.total_nodes}")

            if len(self.peers) == self.total_nodes:
                self.phase = "ELECTION"
                time.sleep(1)
                self.send_vote()

        # ------------------------------
        # 2) Fase de eleição
        # ------------------------------
        elif topic == TOPIC_VOTE:
            cid = data["ClientID"]
            vote = data["VoteID"]

            self.received_votes[cid] = vote

            if self.phase == "ELECTION" and len(self.received_votes) == self.total_nodes:
                self.select_leader()

        # ------------------------------
        # 3) Controle de desafios
        # ------------------------------
        elif topic == TOPIC_NEW_TASK:
            self.phase = "WORKING"
            self.transaction_id = data["TransactionID"]
            self.difficulty = data["Challenge"]
            self.allow_mining = True
            self.transaction_closed = False

            print(f"\n[{self.node_id}] Novo desafio recebido! TX={self.transaction_id}, zeros={self.difficulty}")
            threading.Thread(target=self.mine_loop).start()

        # ------------------------------
        # 4) Verificação de soluções (somente líder)
        # ------------------------------
        elif topic == TOPIC_SUBMIT and self.is_leader:
            if self.transaction_closed:
                return

            tx = data["TransactionID"]
            solution = data["Solution"]

            if tx == self.transaction_id and self.hash_ok(solution):
                self.transaction_closed = True

                print(f"[{self.node_id}] Solução correta recebida de {data['ClientID']}!")

                result = {
                    "ClientID": data["ClientID"],
                    "TransactionID": tx,
                    "Solution": solution,
                    "Result": 1
                }

                self.client.publish(TOPIC_FEEDBACK, json.dumps(result))

                threading.Timer(5, self.create_new_challenge).start()

        # ------------------------------
        # 5) Recebimento de feedback
        # ------------------------------
        elif topic == TOPIC_FEEDBACK and data["Result"] == 1:
            if self.allow_mining:
                print(f"[{self.node_id}] Desafio finalizado! Vencedor: {data['ClientID']}")
                self.allow_mining = False

    # ===============================
    #  LÓGICA DO SISTEMA
    # ===============================

    def discovery_loop(self):
        while self.phase == "DISCOVERY":
            packet = {"ClientID": self.node_id}
            self.client.publish(TOPIC_INIT, json.dumps(packet))
            time.sleep(1.2)

    def send_vote(self):
        packet = {"ClientID": self.node_id, "VoteID": self.vote_number}
        print(f"[{self.node_id}] Enviando voto...")
        self.client.publish(TOPIC_VOTE, json.dumps(packet))

    def select_leader(self):
        high_vote = -1
        selected = None

        for cid, vote in self.received_votes.items():
            if vote > high_vote or (vote == high_vote and cid > selected):
                high_vote = vote
                selected = cid

        print(f"[{self.node_id}] Líder eleito: {selected}")

        if selected == self.node_id:
            self.is_leader = True
            print(f"[{self.node_id}] Sou o líder do grupo!")
            time.sleep(2)
            self.create_new_challenge()

    def create_new_challenge(self):
        if not self.is_leader:
            return
        
        self.transaction_id += 1
        self.difficulty = random.randint(1, 20)

        packet = {
            "TransactionID": self.transaction_id,
            "Challenge": self.difficulty
        }

        self.client.publish(TOPIC_NEW_TASK, json.dumps(packet))

    # ------------------------------
    # Mineração
    # ------------------------------
    def mine_loop(self):
        target = "0" * self.difficulty
        nonce = 0

        print(f"[{self.node_id}] Iniciando mineração...")

        current_tx = self.transaction_id

        while self.allow_mining and current_tx == self.transaction_id:
            candidate = f"{self.node_id}|{self.transaction_id}|{nonce}"
            hashed = hashlib.sha1(candidate.encode()).hexdigest()

            if hashed.startswith(target):
                print(f"[{self.node_id}] Solução encontrada! Hash: {hashed}")

                packet = {
                    "ClientID": self.node_id,
                    "TransactionID": self.transaction_id,
                    "Solution": candidate
                }

                self.client.publish(TOPIC_SUBMIT, json.dumps(packet))
                self.allow_mining = False
                break

            nonce += 1

    def hash_ok(self, sol):
        h = hashlib.sha1(sol.encode()).hexdigest()
        return h.startswith("0" * self.difficulty)

    # ------------------------------
    # Inicialização
    # ------------------------------
    def start(self):
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_forever()


# ===============================
#   Execução
# ===============================

if __name__ == "__main__":
    total = sys.argv[1] if len(sys.argv) > 1 else 3
    node = DistributedNode(total)
    node.start()
