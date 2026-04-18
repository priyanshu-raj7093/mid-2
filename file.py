import json
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

# ============= DATA MODELS =============

class Book:
    """Book model class"""
    def __init__(self, book_id: str, title: str, author: str, isbn: str, 
                 total_copies: int, available_copies: int = None):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.isbn = isbn
        self.total_copies = total_copies
        self.available_copies = available_copies or total_copies
    
    def to_dict(self) -> Dict:
        """Convert book object to dictionary"""
        return {
            'book_id': self.book_id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'total_copies': self.total_copies,
            'available_copies': self.available_copies
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Book':
        """Create book object from dictionary"""
        return cls(
            data['book_id'],
            data['title'],
            data['author'],
            data['isbn'],
            data['total_copies'],
            data['available_copies']
        )

class User:
    """User model class"""
    def __init__(self, user_id: str, name: str, email: str, phone: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.phone = phone
        self.borrowed_books: List[str] = []  # List of book_ids
    
    def to_dict(self) -> Dict:
        """Convert user object to dictionary"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'borrowed_books': self.borrowed_books
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create user object from dictionary"""
        user = cls(
            data['user_id'],
            data['name'],
            data['email'],
            data['phone']
        )
        user.borrowed_books = data.get('borrowed_books', [])
        return user

class Transaction:
    """Transaction model for book issuance and returns"""
    def __init__(self, transaction_id: str, book_id: str, user_id: str, 
                 issue_date: date, due_date: date, return_date: date = None):
        self.transaction_id = transaction_id
        self.book_id = book_id
        self.user_id = user_id
        self.issue_date = issue_date
        self.due_date = due_date
        self.return_date = return_date
    
    def calculate_fine(self, fine_per_day: float = 5.0) -> float:
        """Calculate fine for late return"""
        if self.return_date is None:
            return 0.0
        
        if self.return_date > self.due_date:
            days_late = (self.return_date - self.due_date).days
            return days_late * fine_per_day
        return 0.0
    
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'book_id': self.book_id,
            'user_id': self.user_id,
            'issue_date': self.issue_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'return_date': self.return_date.isoformat() if self.return_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        """Create transaction from dictionary"""
        return cls(
            data['transaction_id'],
            data['book_id'],
            data['user_id'],
            datetime.fromisoformat(data['issue_date']).date(),
            datetime.fromisoformat(data['due_date']).date(),
            datetime.fromisoformat(data['return_date']).date() if data['return_date'] else None
        )

# ============= LIBRARY MANAGEMENT SYSTEM =============

class LibraryManagementSystem:
    """Main library management system class"""
    
    def __init__(self, data_file: str = 'library_data.json'):
        self.data_file = data_file
        self.books: Dict[str, Book] = {}
        self.users: Dict[str, User] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.fine_per_day = 5.0
        self.load_data()
    
    # ============= BOOK MANAGEMENT =============
    
    def add_book(self, book: Book) -> bool:
        """Add a new book to the library"""
        if book.book_id in self.books:
            return False
        self.books[book.book_id] = book
        self.save_data()
        return True
    
    def search_books(self, query: str) -> List[Book]:
        """Search books by title or author"""
        query = query.lower()
        results = []
        for book in self.books.values():
            if query in book.title.lower() or query in book.author.lower():
                results.append(book)
        return results
    
    def display_available_books(self) -> List[Book]:
        """Display all available books"""
        return [book for book in self.books.values() if book.available_copies > 0]
    
    def display_issued_books(self) -> List[Dict]:
        """Display all currently issued books with user information"""
        issued_books = []
        for trans in self.transactions.values():
            if trans.return_date is None:  # Book not returned yet
                book = self.books.get(trans.book_id)
                user = self.users.get(trans.user_id)
                if book and user:
                    issued_books.append({
                        'book': book,
                        'user': user,
                        'issue_date': trans.issue_date,
                        'due_date': trans.due_date
                    })
        return issued_books
    
    # ============= USER MANAGEMENT =============
    
    def add_user(self, user: User) -> bool:
        """Add a new user"""
        if user.user_id in self.users:
            return False
        self.users[user.user_id] = user
        self.save_data()
        return True
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_borrowed_books(self, user_id: str) -> List[Dict]:
        """Get all books borrowed by a user"""
        user = self.users.get(user_id)
        if not user:
            return []
        
        borrowed = []
        for book_id in user.borrowed_books:
            book = self.books.get(book_id)
            if book:
                # Find the active transaction for this book
                for trans in self.transactions.values():
                    if (trans.book_id == book_id and 
                        trans.user_id == user_id and 
                        trans.return_date is None):
                        borrowed.append({
                            'book': book,
                            'issue_date': trans.issue_date,
                            'due_date': trans.due_date
                        })
                        break
        return borrowed
    
    # ============= BOOK ISSUE AND RETURN =============
    
    def issue_book(self, book_id: str, user_id: str, days_to_return: int = 14) -> Optional[str]:
        """Issue a book to a user"""
        # Validate book
        book = self.books.get(book_id)
        if not book:
            return "Book not found"
        
        if book.available_copies <= 0:
            return "No copies available"
        
        # Validate user
        user = self.users.get(user_id)
        if not user:
            return "User not found"
        
        # Check if user has already borrowed this book
        if book_id in user.borrowed_books:
            return "User already has this book"
        
        # Create transaction
        transaction_id = f"T{len(self.transactions) + 1}"
        issue_date = date.today()
        due_date = issue_date + timedelta(days=days_to_return)
        
        transaction = Transaction(transaction_id, book_id, user_id, issue_date, due_date)
        self.transactions[transaction_id] = transaction
        
        # Update records
        book.available_copies -= 1
        user.borrowed_books.append(book_id)
        
        self.save_data()
        return transaction_id
    
    def return_book(self, book_id: str, user_id: str) -> Dict:
        """Return a book and calculate fine if any"""
        # Find the active transaction
        active_transaction = None
        for trans in self.transactions.values():
            if (trans.book_id == book_id and 
                trans.user_id == user_id and 
                trans.return_date is None):
                active_transaction = trans
                break
        
        if not active_transaction:
            return {'success': False, 'message': 'No active transaction found'}
        
        # Process return
        active_transaction.return_date = date.today()
        fine = active_transaction.calculate_fine(self.fine_per_day)
        
        # Update records
        book = self.books.get(book_id)
        user = self.users.get(user_id)
        
        if book and user:
            book.available_copies += 1
            user.borrowed_books.remove(book_id)
        
        self.save_data()
        
        return {
            'success': True,
            'fine': fine,
            'due_date': active_transaction.due_date,
            'return_date': active_transaction.return_date,
            'message': f"Book returned successfully. Fine: ₹{fine}" if fine > 0 else "Book returned successfully. No fine."
        }
    
    # ============= DATA PERSISTENCE =============
    
    def save_data(self):
        """Save all data to JSON file (backup)"""
        data = {
            'books': {bid: book.to_dict() for bid, book in self.books.items()},
            'users': {uid: user.to_dict() for uid, user in self.users.items()},
            'transactions': {tid: trans.to_dict() for tid, trans in self.transactions.items()},
            'fine_per_day': self.fine_per_day
        }
        
        # Create backup before saving
        self.create_backup()
        
        # Save current data
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_data(self):
        """Load data from JSON file"""
        if not os.path.exists(self.data_file):
            return
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Load books
            for book_id, book_data in data.get('books', {}).items():
                self.books[book_id] = Book.from_dict(book_data)
            
            # Load users
            for user_id, user_data in data.get('users', {}).items():
                self.users[user_id] = User.from_dict(user_data)
            
            # Load transactions
            for trans_id, trans_data in data.get('transactions', {}).items():
                self.transactions[trans_id] = Transaction.from_dict(trans_data)
            
            # Load fine rate
            self.fine_per_day = data.get('fine_per_day', 5.0)
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def create_backup(self):
        """Create a backup of current data"""
        backup_file = f"{self.data_file}.backup"
        if os.path.exists(self.data_file):
            import shutil
            shutil.copy2(self.data_file, backup_file)
    
    def restore_backup(self) -> bool:
        """Restore data from backup"""
        backup_file = f"{self.data_file}.backup"
        if os.path.exists(backup_file):
            import shutil
            shutil.copy2(backup_file, self.data_file)
            self.load_data()
            return True
        return False
    
    # ============= DISPLAY FUNCTIONS =============
    
    def display_statistics(self):
        """Display library statistics"""
        total_books = len(self.books)
        total_users = len(self.users)
        available_books = len(self.display_available_books())
        issued_books = len(self.display_issued_books())
        
        print("\n" + "="*50)
        print("LIBRARY STATISTICS")
        print("="*50)
        print(f"Total Books: {total_books}")
        print(f"Available Books: {available_books}")
        print(f"Issued Books: {issued_books}")
        print(f"Total Users: {total_users}")
        print(f"Fine per day: ₹{self.fine_per_day}")

# ============= MAIN APPLICATION =============

def main():
    """Main application interface"""
    library = LibraryManagementSystem()
    
    while True:
        print("\n" + "="*50)
        print("LIBRARY MANAGEMENT SYSTEM")
        print("="*50)
        print("1. Add Book")
        print("2. Add User")
        print("3. Issue Book")
        print("4. Return Book")
        print("5. Search Books")
        print("6. Display Available Books")
        print("7. Display Issued Books")
        print("8. Display User Borrowed Books")
        print("9. Display Statistics")
        print("10. Restore from Backup")
        print("11. Exit")
        
        choice = input("\nEnter your choice (1-11): ").strip()
        
        if choice == '1':
            # Add Book
            book_id = input("Book ID: ")
            title = input("Title: ")
            author = input("Author: ")
            isbn = input("ISBN: ")
            copies = int(input("Total Copies: "))
            
            book = Book(book_id, title, author, isbn, copies)
            if library.add_book(book):
                print("✓ Book added successfully")
            else:
                print("✗ Book ID already exists")
        
        elif choice == '2':
            # Add User
            user_id = input("User ID: ")
            name = input("Name: ")
            email = input("Email: ")
            phone = input("Phone: ")
            
            user = User(user_id, name, email, phone)
            if library.add_user(user):
                print("✓ User added successfully")
            else:
                print("✗ User ID already exists")
        
        elif choice == '3':
            # Issue Book
            book_id = input("Book ID: ")
            user_id = input("User ID: ")
            
            result = library.issue_book(book_id, user_id)
            if isinstance(result, str):
                print(f"✗ {result}")
            else:
                print(f"✓ Book issued successfully. Transaction ID: {result}")
        
        elif choice == '4':
            # Return Book
            book_id = input("Book ID: ")
            user_id = input("User ID: ")
            
            result = library.return_book(book_id, user_id)
            if result['success']:
                print(result['message'])
            else:
                print(f"✗ {result['message']}")
        
        elif choice == '5':
            # Search Books
            query = input("Enter title or author to search: ")
            results = library.search_books(query)
            
            if results:
                print("\nSearch Results:")
                print("-" * 60)
                for book in results:
                    print(f"ID: {book.book_id}, Title: {book.title}, "
                          f"Author: {book.author}, Available: {book.available_copies}/{book.total_copies}")
            else:
                print("No books found")
        
        elif choice == '6':
            # Display Available Books
            available = library.display_available_books()
            
            if available:
                print("\nAvailable Books:")
                print("-" * 60)
                for book in available:
                    print(f"ID: {book.book_id}, Title: {book.title}, "
                          f"Author: {book.author}, Copies: {book.available_copies}")
            else:
                print("No books available")
        
        elif choice == '7':
            # Display Issued Books
            issued = library.display_issued_books()
            
            if issued:
                print("\nIssued Books:")
                print("-" * 60)
                for item in issued:
                    print(f"Book: {item['book'].title}, "
                          f"Borrower: {item['user'].name}, "
                          f"Due Date: {item['due_date']}")
            else:
                print("No books currently issued")
        
        elif choice == '8':
            # Display User Borrowed Books
            user_id = input("Enter User ID: ")
            borrowed = library.get_user_borrowed_books(user_id)
            
            if borrowed:
                print(f"\nBooks borrowed by user {user_id}:")
                print("-" * 60)
                for item in borrowed:
                    print(f"Book: {item['book'].title}, "
                          f"Issue Date: {item['issue_date']}, "
                          f"Due Date: {item['due_date']}")
            else:
                print("User has no borrowed books or user not found")
        
        elif choice == '9':
            # Display Statistics
            library.display_statistics()
        
        elif choice == '10':
            # Restore from Backup
            if library.restore_backup():
                print("✓ Data restored from backup successfully")
            else:
                print("✗ No backup file found")
        
        elif choice == '11':
            # Exit
            print("Thank you for using Library Management System!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()