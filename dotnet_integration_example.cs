// Example .NET Controller to integrate with Python ChatBot Microservice
using Microsoft.AspNetCore.Mvc;
using System.Text;
using System.Text.Json;

[ApiController]
[Route("api/[controller]")]
public class ChatBotController : ControllerBase
{
    private readonly HttpClient _httpClient;
    private readonly string _pythonServiceUrl = "http://localhost:8000"; // Configure this

    public ChatBotController(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    // Initialize Chat Session
    [HttpPost("initialize/{userId}")]
    public async Task<IActionResult> InitializeChat(int userId)
    {
        try
        {
            // Get user's applications and questions data from your database
            var applicationsData = await GetUserApplicationsData(userId);
            var questionsData = await GetUserQuestionsData(userId);

            var request = new
            {
                user_id = userId,
                applications_data = applicationsData,
                questions_data = questionsData
            };

            var json = JsonSerializer.Serialize(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync($"{_pythonServiceUrl}/initialize-chat", content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseContent = await response.Content.ReadAsStringAsync();
                return Ok(JsonSerializer.Deserialize<object>(responseContent));
            }

            return BadRequest("Failed to initialize chat session");
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // Send Message with Streaming Response
    [HttpPost("send-message")]
    public async Task SendMessage([FromBody] SendMessageRequest request)
    {
        try
        {
            var requestData = new
            {
                session_id = request.SessionId,
                message = request.Message
            };

            var json = JsonSerializer.Serialize(requestData);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            // Set response headers for streaming
            Response.Headers.Add("Content-Type", "text/event-stream");
            Response.Headers.Add("Cache-Control", "no-cache");
            Response.Headers.Add("Connection", "keep-alive");

            var response = await _httpClient.PostAsync($"{_pythonServiceUrl}/send-message", content);
            
            if (response.IsSuccessStatusCode)
            {
                // Stream the response back to the client
                await using var stream = await response.Content.ReadAsStreamAsync();
                await stream.CopyToAsync(Response.Body);
            }
            else
            {
                Response.StatusCode = 500;
                await Response.WriteAsync("data: {\"type\":\"error\",\"data\":\"Failed to send message\"}\n\n");
            }
        }
        catch (Exception ex)
        {
            Response.StatusCode = 500;
            await Response.WriteAsync($"data: {{\"type\":\"error\",\"data\":\"{ex.Message}\"}}\n\n");
        }
    }

    // Close Chat Session
    [HttpPost("close-chat")]
    public async Task<IActionResult> CloseChat([FromBody] CloseChatRequest request)
    {
        try
        {
            var requestData = new { session_id = request.SessionId };
            var json = JsonSerializer.Serialize(requestData);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync($"{_pythonServiceUrl}/close-chat", content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseContent = await response.Content.ReadAsStringAsync();
                return Ok(JsonSerializer.Deserialize<object>(responseContent));
            }

            return BadRequest("Failed to close chat session");
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // Helper methods to get data from your database
    private async Task<object> GetUserApplicationsData(int userId)
    {
        // Replace with your actual database query
        // Return the applications data in the same format as your JSON
        return new { /* your applications data */ };
    }

    private async Task<object> GetUserQuestionsData(int userId)
    {
        // Replace with your actual database query  
        // Return the questions data in the same format as your JSON
        return new { /* your questions data */ };
    }
}

// Request models
public class SendMessageRequest
{
    public string SessionId { get; set; }
    public string Message { get; set; }
}

public class CloseChatRequest
{
    public string SessionId { get; set; }
} 