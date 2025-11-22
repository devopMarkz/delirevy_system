# Sistema de Delivery Distribuído - Guia de Execução

## Pré-requisitos

- Docker (versão 20.10 ou superior)
- Docker Compose (versão 1.29 ou superior)

Verificar instalação:
```bash
docker --version
docker-compose --version
```

## Configuração Inicial - SendGrid API Key

Antes de executar o projeto, é necessário configurar a chave de API do SendGrid.

Abra o arquivo `restaurantes-service/main.py` e localize a linha 29:

```python
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'xxx')
```

Substituir 'xxx' pela chave fornecida na DOCUMENTAÇÃO TÉCNICA

Salve o arquivo e prossiga para a inicialização dos serviços.

## Estrutura do Projeto

```
DELIVERY-SYSTEM/
├── docker-compose.yml
├── api-gateway/
├── pedidos-service/
├── restaurantes-service/
└── pagamentos-service/
```

## Iniciar os Serviços

Após configurar a SendGrid API Key, execute:

```bash
docker-compose up -d
```

Este comando inicia todos os serviços:
- API Gateway (porta 8000)
- Pedidos Service (porta 8001)
- Restaurantes Service (porta 8002)
- Pagamentos Service (porta 8003)
- PostgreSQL (portas 5432, 5433, 5434)
- Redis (porta 6379)

Aguarde 10-15 segundos para que todos os serviços inicializem completamente.

## Verificar Status dos Serviços

```bash
docker-compose ps
```

Todos os containers devem estar com status "Up".

## Acessar Documentação Swagger

Cada microsserviço possui documentação interativa:

- Pedidos Service: http://localhost:8001/docs
- Restaurantes Service: http://localhost:8002/docs
- Pagamentos Service: http://localhost:8003/docs

## Testar Conexão

```bash
curl http://localhost:8000/
```

Resposta esperada:
```json
{
  "message": "Delivery System API Gateway",
  "services": {
    "pedidos": "http://pedidos-service:8001/docs",
    "restaurantes": "http://restaurantes-service:8002/docs",
    "pagamentos": "http://pagamentos-service:8003/docs"
  }
}
```

## Comandos Docker Compose Úteis

Visualizar logs de todos os serviços:
```bash
docker-compose logs -f
```

Visualizar logs de um serviço específico:
```bash
docker-compose logs -f pedidos-service
docker-compose logs -f restaurantes-service
docker-compose logs -f pagamentos-service
docker-compose logs -f api-gateway
```

Parar todos os serviços (dados persistem):
```bash
docker-compose stop
```

Parar e remover containers (dados persistem):
```bash
docker-compose down
```

Parar, remover containers e volumes (apaga todos os dados):
```bash
docker-compose down -v
```

Reiniciar todos os serviços:
```bash
docker-compose restart
```

Reiniciar um serviço específico:
```bash
docker-compose restart pedidos-service
```

Reconstruir imagens e iniciar:
```bash
docker-compose up -d --build
```

## Acessar Bancos de Dados

Conectar ao PostgreSQL de pedidos:
```bash
docker-compose exec pedidos-db psql -U user -d pedidosdb
```

Dentro do psql:
```sql
\dt                    -- Listar tabelas
SELECT * FROM pedidos; -- Ver pedidos
\q                     -- Sair
```

Conectar ao PostgreSQL de restaurantes:
```bash
docker-compose exec restaurantes-db psql -U user -d restaurantesdb
```

Conectar ao PostgreSQL de pagamentos:
```bash
docker-compose exec pagamentos-db psql -U user -d pagamentosdb
```

Conectar ao Redis:
```bash
docker-compose exec redis redis-cli
```

Dentro do Redis CLI:
```
PING
KEYS *
GET key_name
EXIT
```

## Fluxo Típico de Testes

1. Criar restaurante via POST /restaurantes
2. Criar categoria via POST /categorias
3. Criar produto via POST /produtos
4. Criar pedido via POST /pedidos (com validações automáticas)
5. Criar pagamento via POST /pagamentos (processado em background)
6. Atualizar status do pedido via PUT /pedidos/{id}/status
7. Criar estorno via POST /estornos (se necessário)

Consulte a documentação técnica para detalhes sobre modelos de dados e fluxos de negócio.
Importe no Postman a Collection salva na pasta raiz do projeto para facilitar os testes.

## Parar Execução

Para parar todos os serviços:
```bash
docker-compose down
```

Os dados persistem em volumes Docker. Para remover dados também:
```bash
docker-compose down -v
```
