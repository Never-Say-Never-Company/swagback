from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework import status
from swag.nsnapp.serializer import UserSerializer
from .models import User

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = User.objects(username=username).first()
        if user and user.check_password(password):
            return Response({'message': 'Login bem-sucedido!'}, status=status.HTTP_200_OK)
        return Response({'error': 'Usuário ou senha incorretos.'}, status=status.HTTP_401_UNAUTHORIZED)
    

class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = User(username=serializer.validated_data['username'])
        user.set_password(serializer.validated_data['password'])
        user.save()

class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
        if 'username' in self.request.data:
            user.username = self.request.data['username']
        user.save()