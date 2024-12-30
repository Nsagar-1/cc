class User:
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password


class BSTNode:
    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.parent = None

    def insert(self, key, value):
        if key < self.key:
            if self.left is None:
                self.left = BSTNode(key, value)
                self.left.parent = self
            else:
                self.left.insert(key, value)
        elif key > self.key:
            if self.right is None:
                self.right = BSTNode(key, value)
                self.right.parent = self
            else:
                self.right.insert(key, value)
        else:
            self.value = value  # Update value if the key already exists

    def find(self, key):
        if key == self.key:
            return self
        elif key < self.key and self.left:
            return self.left.find(key)
        elif key > self.key and self.right:
            return self.right.find(key)
        return None

    def list_all(self):
        nodes = []
        if self.left:
            nodes.extend(self.left.list_all())
        nodes.append((self.key, self.value))
        if self.right:
            nodes.extend(self.right.list_all())
        return nodes


class TreeMap:
    def __init__(self):
        self.root = None

    def insert(self, key, value):
        if not self.root:
            self.root = BSTNode(key, value)
        else:
            self.root.insert(key, value)
            self.balance_tree()

    def find(self, key):
        return self.root.find(key) if self.root else None

    def update(self, key, value):
        node = self.find(key)
        if node:
            node.value = value
        else:
            self.insert(key, value)

    def balance_tree(self):
        nodes = self.root.list_all()
        self.root = self.make_balanced_bst(nodes)

    def make_balanced_bst(self, nodes):
        if not nodes:
            return None
        mid = len(nodes) // 2
        key, value = nodes[mid]
        root = BSTNode(key, value)
        root.left = self.make_balanced_bst(nodes[:mid])
        root.right = self.make_balanced_bst(nodes[mid + 1:])
        return root

    def list_all(self):
        return self.root.list_all() if self.root else []


class UserDataBase:
    def __init__(self):
        self.users = TreeMap()

    def insert(self, user):
        self.users.insert(user.username, user)

    def find(self, username):
        node = self.users.find(username)
        return node.value if node else None

    def update(self, user):
        self.users.update(user.username, user)

    def list_all(self):
        return [user for _, user in self.users.list_all()]
    

# Usage example
database = UserDataBase()
user1 = User("alice", "alice@example.com", "password123")
user2 = User("bob", "bob@example.com", "password456")

database.insert(user1)
database.insert(user2)

print("All users:", database.list_all())
print("Find user 'alice':", database.find("alice"))


