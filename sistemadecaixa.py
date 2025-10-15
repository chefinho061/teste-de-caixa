import sqlite3
import datetime

# ==============================================================================
# 1. GERENCIADOR DE BANCO DE DADOS (SQLite)
# ==============================================================================

class GerenciadorDB:
    def __init__(self, nome_banco='sistema_caixa_estoque.db'):
        self.conn = sqlite3.connect(nome_banco)
        self.cursor = self.conn.cursor()
        self._criar_tabelas()

    def _criar_tabelas(self):
        # Tabela Produtos
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                codigo TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                preco_compra REAL,
                preco_venda REAL NOT NULL,
                quantidade INTEGER NOT NULL
            );
        """)
        
        # Tabela Vendas
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                total REAL NOT NULL,
                valor_pago REAL
            );
        """)
        
        # Tabela Itens da Venda
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_venda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_venda INTEGER,
                codigo_produto TEXT,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                FOREIGN KEY (id_venda) REFERENCES vendas (id),
                FOREIGN KEY (codigo_produto) REFERENCES produtos (codigo)
            );
        """)
        self.conn.commit()

    def fechar(self):
        self.conn.close()

# ==============================================================================
# 2. PRODUTO (Modelo de Dados)
# ==============================================================================

class Produto:
    def __init__(self, codigo, nome, preco_venda, quantidade, preco_compra=0.0):
        self.codigo = codigo.strip().upper()
        self.nome = nome.strip()
        self.preco_compra = preco_compra
        self.preco_venda = preco_venda
        self.quantidade = quantidade

# ==============================================================================
# 3. ESTOQUE (CRUD de Produtos no DB)
# ==============================================================================

class Estoque:
    def __init__(self, db_manager):
        self.db = db_manager 

    def salvar_produto(self, produto):
        try:
            # Tenta inserir
            sql_insert = """
                INSERT INTO produtos (codigo, nome, preco_compra, preco_venda, quantidade) 
                VALUES (?, ?, ?, ?, ?)
            """
            self.db.cursor.execute(sql_insert, (
                produto.codigo, produto.nome, 
                produto.preco_compra, produto.preco_venda, 
                produto.quantidade
            ))
            print(f"Produto '{produto.nome}' cadastrado com sucesso.")
        
        except sqlite3.IntegrityError:
            # Se já existir, atualiza
            sql_update = """
                UPDATE produtos SET nome = ?, preco_compra = ?, preco_venda = ?, quantidade = ? 
                WHERE codigo = ?
            """
            self.db.cursor.execute(sql_update, (
                produto.nome, produto.preco_compra, 
                produto.preco_venda, produto.quantidade, 
                produto.codigo
            ))
            print(f"Produto '{produto.nome}' atualizado com sucesso.")

        except Exception as e:
            print(f"Erro ao salvar produto: {e}")
            self.db.conn.rollback()
            return

        self.db.conn.commit()

    def buscar_produto(self, codigo):
        self.db.cursor.execute("SELECT * FROM produtos WHERE codigo = ?", (codigo.upper(),))
        registro = self.db.cursor.fetchone()
        
        if registro:
            colunas = ["codigo", "nome", "preco_compra", "preco_venda", "quantidade"]
            return dict(zip(colunas, registro))
        return None

    def listar_produtos(self):
        self.db.cursor.execute("SELECT codigo, nome, preco_venda, quantidade FROM produtos ORDER BY nome")
        return self.db.cursor.fetchall()
    
    def remover_produto(self, codigo):
        self.db.cursor.execute("DELETE FROM produtos WHERE codigo = ?", (codigo.upper(),))
        if self.db.cursor.rowcount > 0:
            self.db.conn.commit()
            return True
        return False

    def dar_baixa(self, codigo, quantidade_vendida):
        produto = self.buscar_produto(codigo)
        if produto and produto['quantidade'] >= quantidade_vendida:
            nova_quantidade = produto['quantidade'] - quantidade_vendida
            
            sql = "UPDATE produtos SET quantidade = ? WHERE codigo = ?"
            self.db.cursor.execute(sql, (nova_quantidade, codigo.upper()))
            # Não faz commit aqui, o commit final é feito no SistemaCaixaEstoque
            return True
        return False

# ==============================================================================
# 4. SISTEMA PRINCIPAL (Menus e Orquestração)
# ==============================================================================

class SistemaCaixaEstoque:
    def __init__(self):
        self.db_manager = GerenciadorDB() 
        self.estoque = Estoque(self.db_manager)

    def __del__(self):
        self.db_manager.fechar()

    # --- FUNÇÕES DE ESTOQUE (OPÇÃO 1) ---
    def menu_cadastro_produtos(self):
        while True:
            print("\n--- GERENCIAMENTO DE ESTOQUE ---")
            print("1. Cadastrar/Atualizar Produto")
            print("2. Listar Todos os Produtos")
            print("3. Remover Produto")
            print("4. Voltar ao Menu Principal")
            
            escolha = input("Escolha uma opção: ")
            
            if escolha == '1':
                self._cadastrar_ou_atualizar_produto()
            elif escolha == '2':
                self._listar_produtos()
            elif escolha == '3':
                self._remover_produto()
            elif escolha == '4':
                break
            else:
                print("Opção inválida. Tente novamente.")

    def _cadastrar_ou_atualizar_produto(self):
        codigo = input("Código do Produto (obrigatório): ").strip().upper()
        if not codigo: return

        nome = input("Nome do Produto: ").strip()
        if not nome: return

        try:
            preco_venda = float(input("Preço de Venda: R$ "))
            preco_compra = float(input("Preço de Custo (Compra): R$ "))
            quantidade = int(input("Quantidade Inicial/Atual: "))
        except ValueError:
            print("ERRO: Preços e quantidades devem ser números válidos.")
            return

        novo_produto = Produto(codigo, nome, preco_venda, quantidade, preco_compra)
        self.estoque.salvar_produto(novo_produto)
    
    def _listar_produtos(self):
        produtos = self.estoque.listar_produtos()
        if not produtos:
            print("Nenhum produto cadastrado no estoque.")
            return
        
        print("\n---------------- ESTOQUE ATUAL ----------------")
        print("CÓDIGO | NOME                  | PREÇO VENDA | QTD")
        print("-------------------------------------------------")
        for p in produtos:
            print(f"{p[0]:<6} | {p[1]:<21} | R$ {p[2]:<8.2f} | {p[3]}")
        print("-------------------------------------------------\n")

    def _remover_produto(self):
        codigo = input("Digite o CÓDIGO do produto a ser removido: ").strip().upper()
        produto_existente = self.estoque.buscar_produto(codigo)

        if not produto_existente:
            print(f"ERRO: Produto com código '{codigo}' não encontrado.")
            return
        
        confirmacao = input(f"Tem certeza que deseja remover {produto_existente['nome']}? (s/n): ").lower()
        if confirmacao == 's':
            if self.estoque.remover_produto(codigo):
                print(f"Produto {codigo} removido com sucesso.")
            else:
                print("Erro ao tentar remover o produto.")


    # --- FUNÇÕES DE CAIXA (OPÇÃO 2) ---
    def _registrar_transacao(self, itens_da_venda, total_venda, valor_pago):
        data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. REGISTRAR VENDA
            sql_venda = "INSERT INTO vendas (data_hora, total, valor_pago) VALUES (?, ?, ?)"
            self.db_manager.cursor.execute(sql_venda, (data_hora, total_venda, valor_pago))
            id_venda = self.db_manager.cursor.lastrowid

            # 2. REGISTRAR ITENS E DAR BAIXA NO ESTOQUE
            sql_item = """
                INSERT INTO itens_venda (id_venda, codigo_produto, quantidade, preco_unitario)
                VALUES (?, ?, ?, ?)
            """
            for item in itens_da_venda:
                self.db_manager.cursor.execute(sql_item, (
                    id_venda, item['codigo'], item['qtd'], item['preco_unit']
                ))
                self.estoque.dar_baixa(item['codigo'], item['qtd'])

            self.db_manager.conn.commit()
            return id_venda

        except Exception as e:
            self.db_manager.conn.rollback()
            print(f"ERRO ao registrar venda. Operação desfeita (rollback): {e}")
            return None

    def abrir_caixa(self):
        print("\n--- ABRIR CAIXA (NOVA VENDA) ---")
        itens_da_venda = []
        total_venda = 0.0

        while True:
            codigo = input("Digite o código do produto (ou 'F' para finalizar): ").strip().upper()
            if codigo == 'F': break

            produto_db = self.estoque.buscar_produto(codigo)
            if not produto_db:
                print(f"ERRO: Produto com código '{codigo}' não encontrado.")
                continue

            try:
                qtd = int(input(f"Quantidade de '{produto_db['nome']}' (Estoque: {produto_db['quantidade']}): "))
            except ValueError:
                print("ERRO: Quantidade deve ser um número inteiro.")
                continue
            
            if qtd <= 0 or qtd > produto_db['quantidade']:
                print(f"ERRO: Quantidade inválida. Máximo disponível: {produto_db['quantidade']}.")
                continue
            
            subtotal_item = qtd * produto_db['preco_venda']
            itens_da_venda.append({
                "codigo": codigo, "nome": produto_db['nome'], "qtd": qtd, 
                "preco_unit": produto_db['preco_venda'], "subtotal": subtotal_item
            })
            total_venda += subtotal_item
            
            print(f"-> Item adicionado: {qtd}x {produto_db['nome']} | TOTAL: R$ {total_venda:.2f}")

        if not itens_da_venda: return

        print(f"\nTOTAL A PAGAR: R$ {total_venda:.2f}")
        while True:
            try:
                valor_pago = float(input("Valor recebido do cliente: R$ "))
                if valor_pago >= total_venda: break
                print("ERRO: Valor insuficiente.")
            except ValueError:
                print("ERRO: Valor inválido.")

        troco = valor_pago - total_venda
        print(f"TROCO: R$ {troco:.2f}")
        
        id_venda = self._registrar_transacao(itens_da_venda, total_venda, valor_pago)
        if id_venda is not None:
            print(f"\n--- SUCESSO! Venda finalizada. ID de Venda: {id_venda} ---")


    # --- FUNÇÕES DE RELATÓRIOS (OPÇÃO 3) ---
    def menu_relatorios(self):
        while True:
            print("\n--- VISUALIZAR RELATÓRIOS ---")
            print("1. Histórico de Vendas (Últimas Transações)")
            print("2. Resumo de Lucro Bruto Total")
            print("3. Voltar ao Menu Principal")
            
            escolha = input("Escolha uma opção: ")
            
            if escolha == '1':
                self._historico_vendas()
            elif escolha == '2':
                self._resumo_lucro_bruto()
            elif escolha == '3':
                break
            else:
                print("Opção inválida. Tente novamente.")

    def _historico_vendas(self):
        print("\n----------- HISTÓRICO DE VENDAS -----------")
        sql = "SELECT id, data_hora, total, valor_pago FROM vendas ORDER BY id DESC LIMIT 20"
        self.db_manager.cursor.execute(sql)
        vendas = self.db_manager.cursor.fetchall()
        
        if not vendas:
            print("Nenhuma venda registrada até o momento.")
            return

        for venda in vendas:
            id_venda, data_hora, total, valor_pago = venda
            troco = valor_pago - total
            
            print(f"\n[ VENDA ID: {id_venda} | DATA: {data_hora} ]")
            print(f"  TOTAL: R$ {total:.2f} | PAGO: R$ {valor_pago:.2f} | TROCO: R$ {troco:.2f}")

            sql_itens = "SELECT codigo_produto, quantidade, preco_unitario FROM itens_venda WHERE id_venda = ?"
            self.db_manager.cursor.execute(sql_itens, (id_venda,))
            itens = self.db_manager.cursor.fetchall()
            
            print("  - Itens Vendidos:")
            for item in itens:
                codigo, qtd, preco_unit = item
                subtotal = qtd * preco_unit
                print(f"    -> {qtd}x | CÓD: {codigo} | Unit: R$ {preco_unit:.2f} | Subtotal: R$ {subtotal:.2f}")

        print("-------------------------------------------\n")

    def _resumo_lucro_bruto(self):
        print("\n----------- RESUMO DE LUCRO BRUTO -----------")
        
        # Lucro Bruto Total: Soma (Quantidade Vendida * (Preço Venda Unitário - Preço Custo Unitário))
        sql = """
            SELECT SUM(
                IV.quantidade * (IV.preco_unitario - P.preco_compra)
            )
            FROM itens_venda IV
            JOIN produtos P ON IV.codigo_produto = P.codigo;
        """
        self.db_manager.cursor.execute(sql)
        lucro_bruto_total = self.db_manager.cursor.fetchone()[0] or 0.0
        
        sql_total_faturado = "SELECT SUM(total) FROM vendas"
        self.db_manager.cursor.execute(sql_total_faturado)
        faturamento = self.db_manager.cursor.fetchone()[0] or 0.0

        print(f"Total Faturado (Bruto de Vendas): R$ {faturamento:.2f}")
        print(f"Lucro Bruto Total Acumulado:     R$ {lucro_bruto_total:.2f}")
        print("---------------------------------------------\n")


    # ==========================================================================
    # 5. MENU PRINCIPAL
    # ==========================================================================
    def menu_principal(self):
        print("\n--- Inicializando Sistema de Caixa e Estoque (SQLite) ---")
        
        while True:
            print("\n================ MENU PRINCIPAL ================")
            print("1. Gerenciar Estoque (Cadastro, Edição, Lista)")
            print("2. Abrir Caixa (Nova Venda)")
            print("3. Visualizar Relatórios")
            print("4. Sair do Sistema")
            print("================================================")
            
            escolha = input("Escolha uma opção: ")
            
            if escolha == '1':
                self.menu_cadastro_produtos()
            elif escolha == '2':
                self.abrir_caixa()
            elif escolha == '3':
                self.menu_relatorios()
            elif escolha == '4':
                print("Sistema encerrado. A conexão com o banco de dados foi fechada.")
                break
            else:
                print("Opção inválida.")


if __name__ == '__main__':
    sistema = SistemaCaixaEstoque()
    sistema.menu_principal()